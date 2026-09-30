# Gifgloo Shorts Renderer

이미지·GIF, 자막, 배경음을 JSON에 넣으면 세로 MP4를 만드는 독립 로컬 도구입니다.
`shorts_cloudrift_mkII`의 MoviePy 렌더링·자막 코드를 추려 옮겼습니다.
Gifgloo 백엔드나 기존 쇼츠 프로젝트를 import하지 않습니다.

## 실행

준비된 가상환경에서는 다음과 같이 실행합니다.

```bash
cd /Users/gigcot/projs/gifgloo/gifgloo-shorts-renderer
.venv/bin/python render.py examples/demo.json
```

`output/demo.mp4`가 생성됩니다. 출력 파일이 이미 있으면 중단합니다.
의도적으로 다시 만들 때는 `--overwrite`를 붙입니다.

```bash
.venv/bin/python render.py examples/demo.json --overwrite
.venv/bin/python render.py examples/silent.json
```

다른 환경에서 처음 설치할 때는 Python 3.10 이상으로 가상환경을 생성합니다.
현재 검증 환경은 macOS arm64, Python 3.13입니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

`requirements-lock.txt`는 검증 환경의 전체 의존성 버전 기록입니다.
FFmpeg는 `imageio-ffmpeg`가 제공하는 실행 파일을 사용합니다.

## 입력 JSON

```json
{
  "title": "사진과 GIF 합성",
  "bgm_path": "assets/bgm.mp3",
  "items": [
    {"path": "assets/original.png", "caption": "이 사진을"},
    {"path": "assets/source.gif", "caption": "이 움짤에 넣으면"},
    {"path": "assets/result.gif", "caption": "이렇게 됨"}
  ],
  "output_path": "output/short.mp4"
}
```

모든 상대 경로는 실행 위치가 아닌 **해당 JSON 파일이 있는 디렉토리** 기준입니다.
절대 경로도 사용할 수 있습니다. 배열 순서대로 소재가 표시됩니다.

- `title`: 영상 내내 표시할 상단 문구. 빈 문자열이면 생략합니다.
- `items`: 소재 목록. 각 항목에는 `path`와 `caption`이 필요합니다.
- `caption`: 해당 소재의 하단 자막. 빈 문자열이면 생략합니다.
- `bgm_path`: 배경음 파일. 배경음이 필요 없으면 키 자체를 생략합니다.
- `output_path`: 출력 MP4 경로.

`seconds_per_image`, `start`, `duration` 같은 시간 입력은 받지 않습니다.
지원하지 않는 키는 오타나 오해를 숨기지 않도록 오류로 처리합니다.

## 기존 시간 처리와 화면 배치

OCR·TTS 없이 준비하는 일반 이미지와 GIF는 기존 기본값인 **1.7초** 동안 표시합니다.
GIF의 원래 길이를 자동으로 표시 시간으로 쓰지 않으며, 정해진 표시 시간에 맞춰 반복·절단합니다.
소재 3개를 넣은 기본 예제의 길이는 5.1초입니다.

하단 자막은 기존처럼 15자 기준으로 분할한 뒤 문자 수에 비례해 해당 소재의 표시 시간에 나눠 보여줍니다.
TTS가 없어도 자막이 나옵니다. 긴 자막도 전체 시간을 늘리지 않으므로 짧은 문구가 적합합니다.

| 항목 | 값 |
| --- | --- |
| 출력 | 1080 × 1920, 30fps |
| 이미지 영역 | y=450~1300, 원본 비율 유지 |
| 배경 | 동일 소재의 블러 처리 |
| 하단 자막 | y=1305, NanumSquareRoundEB 57px, 흰색 |
| 상단 문구 | y=100, BlackHanSans 100px, 청록색, 10자 기준 줄바꿈 |
| 배경음 | 원본 음량의 30%, 전체 영상 길이만큼 반복·절단 |
| 인코딩 | H.264 / yuv420p, 오디오가 있으면 AAC |

## 이미 생성한 TTS 파일 사용

필요한 소재에만 `tts_path`를 추가할 수 있습니다.

```json
{"path": "assets/result.gif", "caption": "완성된 모습입니다", "tts_path": "assets/voice.mp3"}
```

자막과 TTS가 있으면 기존처럼 음성 길이를 기준으로 이미지·자막을 배치합니다.
TTS만 있고 자막이 비어 있으면 이미지 표시 시간은 최소 1.7초를 보장합니다.
TTS 생성 API 호출은 포함하지 않습니다.

## 구성과 범위

- `render.py`: 명령줄 진입점.
- `shorts_renderer/input.py`: JSON 검증, 경로 처리, 작은 입력 dataclass.
- `shorts_renderer/captions.py`: 기존 자막 분할·이미지 생성 로직.
- `shorts_renderer/rendering.py`: 소재별 장면 생성, 배치, 연결, MP4 출력.
- `assets/fonts/`: 기존 프로젝트에서 복사한 두 폰트.
- `examples/`: 입력 JSON과 프로그램으로 생성한 데모 소재·배경음. 실제 서비스 결과물이 아닙니다.

원본은 `shorts_cloudrift_mkII/cloudrift/test/mkII_analysis_graph_test/`의
`rendering/moviepy/video_rendering.py`, `timeline_build.py`, `customized_moviepy.py`,
`rendering/prepare_element/prepare_caption_image.py`입니다.
기존 `PostState`, `NodeTemplate`, 게시글 분석·OCR·시나리오 생성·업로드 의존성은 가져오지 않았습니다.
입력 하나를 이미지 하나와 자막 묶음으로 단순화했습니다.
MP4 화면 녹화 입력, 효과음 검색, 자동 업로드는 포함하지 않습니다.

## 확인

```bash
.venv/bin/python -m unittest discover -s tests -v
```

JSON 상대 경로, 시간 파라미터 거부, 무음 자막 위치, GIF 반복, 자막 시간 분배,
음성 파일 길이 적용을 확인합니다.
예제 소재가 없는 새 복사본에서는 `examples/create_demo_assets.py`로 생성할 수 있습니다.
