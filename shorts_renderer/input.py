import json
from dataclasses import dataclass
from pathlib import Path


class RenderInputError(ValueError):
    pass


@dataclass(frozen=True)
class RenderItem:
    path: Path
    caption: str
    tts_path: Path | None


@dataclass(frozen=True)
class RenderCommand:
    title: str
    items: tuple[RenderItem, ...]
    bgm_path: Path | None
    output_path: Path


def validate_keys(value, required, optional, label):
    if not isinstance(value, dict):
        raise RenderInputError(f"{label}: JSON 객체여야 합니다.")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise RenderInputError(
            f"{label}: 누락된 키={sorted(missing)}, 지원하지 않는 키={sorted(unknown)}"
        )


def resolve_path(value, base_dir, label, *, must_exist):
    if not isinstance(value, str) or not value.strip():
        raise RenderInputError(f"{label}: 비어 있지 않은 파일 경로가 필요합니다.")
    path = (base_dir / value).resolve()
    if must_exist and not path.is_file():
        raise RenderInputError(f"{label}: 파일을 찾을 수 없습니다: {path}")
    return path


def load_command(json_path: str | Path) -> RenderCommand:
    json_path = Path(json_path).resolve()
    with json_path.open(encoding="utf-8") as file:
        data = json.load(file)
    validate_keys(data, {"title", "items", "output_path"}, {"bgm_path"}, "입력")
    if not isinstance(data["title"], str):
        raise RenderInputError("title은 문자열이어야 합니다.")
    if not isinstance(data["items"], list) or not data["items"]:
        raise RenderInputError("items에는 소재가 하나 이상 필요합니다.")

    base_dir = json_path.parent
    items = []
    for index, item in enumerate(data["items"]):
        label = f"items[{index}]"
        validate_keys(item, {"path", "caption"}, {"tts_path"}, label)
        if not isinstance(item["caption"], str):
            raise RenderInputError(f"{label}.caption은 문자열이어야 합니다.")
        path = resolve_path(item["path"], base_dir, f"{label}.path", must_exist=True)
        tts_path = (
            resolve_path(item["tts_path"], base_dir, f"{label}.tts_path", must_exist=True)
            if "tts_path" in item else None
        )
        items.append(RenderItem(path, item["caption"].strip(), tts_path))

    bgm_path = (
        resolve_path(data["bgm_path"], base_dir, "bgm_path", must_exist=True)
        if "bgm_path" in data else None
    )
    output_path = resolve_path(data["output_path"], base_dir, "output_path", must_exist=False)
    if output_path.suffix.lower() != ".mp4":
        raise RenderInputError("output_path의 확장자는 .mp4여야 합니다.")
    sources = {json_path, *(item.path for item in items)}
    sources.update(item.tts_path for item in items if item.tts_path is not None)
    if bgm_path is not None:
        sources.add(bgm_path)
    if output_path in sources:
        raise RenderInputError("출력 경로는 입력 파일과 달라야 합니다.")
    return RenderCommand(data["title"].strip(), tuple(items), bgm_path, output_path)
