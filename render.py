import argparse

from shorts_renderer.input import load_command
from shorts_renderer.rendering import render_video


def main():
    parser = argparse.ArgumentParser(description="JSON으로 이미지·GIF 쇼츠 렌더링")
    parser.add_argument("json_path", help="입력 JSON 파일 경로")
    parser.add_argument("--overwrite", action="store_true", help="기존 출력 파일 덮어쓰기")
    args = parser.parse_args()
    command = load_command(args.json_path)
    result = render_video(command, overwrite=args.overwrite)
    print(f"완료: {result}")


if __name__ == "__main__":
    main()
