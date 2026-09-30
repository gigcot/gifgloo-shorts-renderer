import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from shorts_renderer.input import RenderInputError, RenderItem, load_command
from shorts_renderer.rendering import build_beat_clip, build_caption_timeline


ROOT = Path(__file__).resolve().parent.parent


class RendererTests(unittest.TestCase):
    def test_paths_are_relative_to_json(self):
        command = load_command(ROOT / "examples" / "demo.json")
        self.assertEqual(command.items[0].path, ROOT / "examples/assets/original.png")
        self.assertEqual(command.output_path, ROOT / "output/demo.mp4")

    def test_rejects_time_parameter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps({
                "title": "test", "items": [], "output_path": "out.mp4",
                "seconds_per_image": 3,
            }), encoding="utf-8")
            with self.assertRaisesRegex(RenderInputError, "seconds_per_image"):
                load_command(path)

    def test_silent_caption_and_image_keep_existing_layout(self):
        item = RenderItem(ROOT / "examples/assets/original.png", "무음 자막", None)
        with ExitStack() as resources:
            beat = build_beat_clip(item, resources)
            frame = beat.get_frame(0.5)
            self.assertEqual(beat.size, (1080, 1920))
            self.assertEqual(beat.duration, 1.7)
            self.assertIsNone(beat.audio)
            self.assertGreater(np.count_nonzero(frame[450:1300]), 0)
            self.assertGreater(np.count_nonzero(frame[1305:1400]), 0)
            self.assertEqual(np.count_nonzero(frame[1400:]), 0)

    def test_animated_gif_uses_existing_minimum_and_loops(self):
        item = RenderItem(ROOT / "examples/assets/source.gif", "", None)
        with ExitStack() as resources:
            beat = build_beat_clip(item, resources)
            self.assertEqual(beat.duration, 1.7)
            first = beat.get_frame(0.1)
            later = beat.get_frame(0.6)
            repeated = beat.get_frame(1.1)
            self.assertFalse(np.array_equal(first, later))
            self.assertTrue(np.array_equal(first, repeated))

    def test_caption_chunks_fill_silent_duration(self):
        events = build_caption_timeline("음성이 없어도 긴 자막을 나누어 순서대로 표시합니다", 1.7)
        self.assertGreater(len(events), 1)
        self.assertEqual(events[0][1], 0)
        self.assertAlmostEqual(sum(duration for _, _, duration in events), 1.7)
        for previous, following in zip(events, events[1:]):
            self.assertAlmostEqual(previous[1] + previous[2], following[1])

    def test_tts_file_controls_duration(self):
        item = RenderItem(
            ROOT / "examples/assets/original.png", "음성 길이에 맞춤",
            ROOT / "examples/assets/bgm.wav",
        )
        with ExitStack() as resources:
            beat = build_beat_clip(item, resources)
            self.assertAlmostEqual(beat.duration, 2.0, places=2)
            self.assertIsNotNone(beat.audio)


if __name__ == "__main__":
    unittest.main()
