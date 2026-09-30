from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from moviepy import (
    AudioFileClip, CompositeAudioClip, CompositeVideoClip, ImageClip,
    VideoFileClip, concatenate_videoclips,
)
from moviepy.audio.fx import AudioLoop, MultiplyVolume
from moviepy.video.fx import Loop
from PIL import Image, ImageFilter

from shorts_renderer.captions import (
    TITLE_FONT, group_subtitle_image, make_caption_images, split_text,
)
from shorts_renderer.input import RenderCommand, RenderInputError


SCREEN_SIZE = (1080, 1920)
IMAGE_TOP = 450
IMAGE_BOTTOM = 1300
CAPTION_TOP = IMAGE_BOTTOM + 5
MIN_DISPLAY = 1.7


def build_caption_timeline(text: str, duration: float):
    chunks = split_text(text)
    total_length = sum(len(chunk) for chunk in chunks)
    offset = 0.0
    events = []
    for chunk in chunks:
        chunk_duration = duration * len(chunk) / total_length
        events.append((chunk, offset, chunk_duration))
        offset += chunk_duration
    return events


def build_beat_clip(item, resources):
    speech = (
        resources.enter_context(AudioFileClip(str(item.tts_path)))
        if item.tts_path is not None else None
    )
    duration = MIN_DISPLAY
    if speech is not None:
        duration = speech.duration if item.caption else max(MIN_DISPLAY, speech.duration)

    with Image.open(item.path) as image:
        animated = getattr(image, "is_animated", False)
        width, height = image.size
        still_frame = np.array(image.convert("RGBA")) if not animated else None

    source = (
        resources.enter_context(VideoFileClip(str(item.path), audio=False))
        if animated else ImageClip(still_frame)
    )
    image_height = IMAGE_BOTTOM - IMAGE_TOP
    wide = width / height > SCREEN_SIZE[0] / image_height
    foreground = source.resized(width=SCREEN_SIZE[0]) if wide else source.resized(height=image_height)
    background = source.resized(height=image_height) if wide else source.resized(width=SCREEN_SIZE[0])

    if animated:
        background = background.image_transform(
            lambda frame: np.array(Image.fromarray(frame).filter(ImageFilter.GaussianBlur(20)))
        )
    else:
        blurred = np.array(Image.fromarray(background.get_frame(0)).filter(ImageFilter.GaussianBlur(20)))
        background = ImageClip(blurred)

    if background.h > image_height:
        y1 = (background.h - image_height) // 2
        background = background.cropped(y1=y1, y2=y1 + image_height)
    if animated:
        foreground = foreground.with_effects([Loop(duration=duration)])
        background = background.with_effects([Loop(duration=duration)])

    foreground = foreground.with_position(
        ("center", IMAGE_TOP + (image_height - foreground.h) // 2)
    ).with_duration(duration)
    background = background.with_position(("center", IMAGE_TOP)).with_duration(duration)
    layers = [background, foreground]

    for text, start, caption_duration in build_caption_timeline(item.caption, duration):
        caption = make_caption_images([text])[0]
        layers.append(
            ImageClip(np.array(caption))
            .with_start(start)
            .with_duration(caption_duration)
            .with_position(("center", CAPTION_TOP))
        )

    beat = resources.enter_context(
        CompositeVideoClip(layers, size=SCREEN_SIZE, bg_color=(0, 0, 0))
    ).with_duration(duration)
    if speech is not None:
        beat = beat.with_audio(speech)
    return beat


def render_video(command: RenderCommand, *, overwrite: bool = False) -> Path:
    if command.output_path.exists() and not overwrite:
        raise RenderInputError(
            f"출력 파일이 이미 있습니다: {command.output_path}\n"
            "다른 output_path를 지정하거나 --overwrite를 사용하세요."
        )

    with ExitStack() as resources:
        beats = [build_beat_clip(item, resources) for item in command.items]
        concatenated = resources.enter_context(concatenate_videoclips(beats, method="compose"))
        layers = [concatenated]
        if command.title:
            title_image = group_subtitle_image(make_caption_images(
                split_text(command.title, 10), TITLE_FONT, 100, (51, 204, 255, 255)
            ))
            layers.append(
                ImageClip(np.array(title_image))
                .with_duration(concatenated.duration)
                .with_position(("center", 100))
            )
        final = resources.enter_context(
            CompositeVideoClip(layers, size=SCREEN_SIZE, bg_color=(0, 0, 0))
        ).with_duration(concatenated.duration)

        audio_clips = []
        if concatenated.audio is not None:
            audio_clips.append(concatenated.audio)
        if command.bgm_path is not None:
            bgm = resources.enter_context(AudioFileClip(str(command.bgm_path)))
            audio_clips.append(bgm.with_effects([
                AudioLoop(duration=concatenated.duration), MultiplyVolume(0.3),
            ]))
        if audio_clips:
            audio = resources.enter_context(CompositeAudioClip(audio_clips))
            final = final.with_audio(audio.with_duration(concatenated.duration).with_fps(44100))

        command.output_path.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="shorts-render-") as temporary:
            final.write_videofile(
                str(command.output_path), fps=30, codec="libx264", bitrate="5000k",
                audio_codec="aac", audio_bitrate="320k", audio_fps=44100,
                temp_audiofile=str(Path(temporary) / "audio.m4a"),
                ffmpeg_params=["-pix_fmt", "yuv420p"],
            )
    return command.output_path
