import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
CAPTION_FONT = FONT_DIR / "NanumSquareRoundEB.ttf"
TITLE_FONT = FONT_DIR / "BlackHanSans-Regular.ttf"


def split_text(text: str, max_len: int = 15) -> list[str]:
    lines = []
    text = text.strip()
    while text:
        if len(text) <= max_len:
            lines.append(text)
            break
        candidates = [match.start() for match in re.finditer(r"[ .,!?]", text[:max_len + 1])]
        split_at = max(candidates) + 1 if candidates else max_len
        lines.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return lines


def make_caption_images(lines, font_path=CAPTION_FONT, font_size=57,
                        color=(255, 255, 255, 255)):
    font = ImageFont.truetype(str(font_path), font_size)
    images = []
    for text in lines:
        bbox = font.getbbox(text)
        ascent, descent = font.getmetrics()
        image = Image.new("RGBA", (bbox[2] - bbox[0], ascent + descent), (0, 0, 0, 0))
        ImageDraw.Draw(image).text((-bbox[0], 0), text, font=font, fill=color)
        images.append(image)
    return images


def group_subtitle_image(images, line_gap=10):
    width = max(image.width for image in images)
    height = sum(image.height for image in images) + line_gap * (len(images) - 1)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    y = 0
    for image in images:
        canvas.paste(image, ((width - image.width) // 2, y))
        y += image.height + line_gap
    return canvas
