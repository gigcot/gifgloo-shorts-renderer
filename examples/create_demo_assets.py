from pathlib import Path
import wave

import numpy as np
from PIL import Image, ImageDraw


def main():
    directory = Path(__file__).resolve().parent / "assets"
    directory.mkdir(exist_ok=True)
    paths = [directory / name for name in ("original.png", "source.gif", "result.gif", "bgm.wav")]
    if any(path.exists() for path in paths):
        raise FileExistsError("예제 소재가 이미 있습니다. 기존 파일은 보존합니다.")

    portrait = Image.new("RGB", (480, 480), "#173A35")
    draw = ImageDraw.Draw(portrait)
    draw.ellipse((90, 70, 390, 370), fill="#FFAF50")
    draw.ellipse((165, 160, 190, 195), fill="#242424")
    draw.ellipse((290, 160, 315, 195), fill="#242424")
    draw.arc((185, 200, 295, 290), 0, 180, fill="#242424", width=10)
    portrait.save(paths[0])

    source_frames, result_frames = [], []
    for index in range(10):
        x = 90 + int(230 * (1 - np.cos(2 * np.pi * index / 10)) / 2)
        source = Image.new("RGB", (640, 480), "#203759")
        draw = ImageDraw.Draw(source)
        draw.rounded_rectangle((x, 125, x + 220, 345), radius=30, fill="#67D5C7")
        source_frames.append(source)
        result = source.copy()
        result.paste(portrait.resize((190, 190)), (x + 15, 140))
        result_frames.append(result)
    for frames, path in ((source_frames, paths[1]), (result_frames, paths[2])):
        frames[0].save(
            path, save_all=True, append_images=frames[1:],
            duration=100, loop=0, disposal=2, optimize=False,
        )

    rate = 44100
    t = np.arange(rate * 2) / rate
    signal = sum(np.sin(2 * np.pi * frequency * t) for frequency in (220, 277.18, 329.63)) / 3
    envelope = np.minimum(t / 0.08, 1) * np.minimum((2 - t) / 0.08, 1)
    samples = (signal * envelope * 0.15 * 32767).astype("<i2")
    with wave.open(str(paths[3]), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(samples.tobytes())
    print(f"예제 소재 생성: {directory}")


if __name__ == "__main__":
    main()
