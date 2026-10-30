"""QA — Video renderer: phụ đề, cảnh, fallback ảnh (không cần ffmpeg)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from render import ass_events, ass_time, resolve_image, scene_spans, subtitle_chunks  # noqa: E402


def w(text, start, end):
    return {"text": text, "type": "word", "start": start, "end": end}


class TestSubtitles(unittest.TestCase):
    def test_breaks_at_sentence_end(self):
        words = [w("Hello", 0, 0.4), w("there.", 0.5, 1.0), w("Next", 1.2, 1.5)]
        chunks = subtitle_chunks(words)
        self.assertEqual([c[0] for c in chunks], ["Hello there.", "Next"])
        self.assertEqual(chunks[0][1:], (0, 1.0))

    def test_breaks_long_lines(self):
        words = [w("word", i, i + 0.5) for i in range(20)]
        for text, _, _ in subtitle_chunks(words, max_chars=20):
            self.assertLessEqual(len(text), 24)

    def test_skips_non_words(self):
        words = [w("Hi.", 0, 0.5), {"text": " ", "type": "spacing", "start": 0.5, "end": 0.6}]
        self.assertEqual(len(subtitle_chunks(words)), 1)

    def test_events_stop_at_limit(self):
        chunks = [("a", 0.0, 1.0), ("b", 5.0, 6.0)]
        self.assertEqual(len(ass_events(chunks, limit=3.0)), 1)

    def test_ass_time(self):
        self.assertEqual(ass_time(63.92), "0:01:03.92")


class TestScenes(unittest.TestCase):
    def test_spans_cover_until_total(self):
        scenes = [{"start": 0, "image": "s01"}, {"start": 4, "image": "s02"}]
        self.assertEqual(scene_spans(scenes, 10, 10), [("s01", 0, 4), ("s02", 4, 10)])

    def test_spans_cut_at_preview(self):
        scenes = [{"start": 0, "image": "s01"}, {"start": 4, "image": "s02"}, {"start": 9, "image": "s03"}]
        self.assertEqual(scene_spans(scenes, 20, 6), [("s01", 0, 4), ("s02", 4, 6)])

    def test_fallback_image(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "img"))
            open(os.path.join(d, "img", "s01.png"), "w").close()
            ep = {"dir": d, "fallback": {"s05": "s03", "s03": "s01"}}
            self.assertTrue(resolve_image(ep, "s05").endswith("s01.png"))
            with self.assertRaises(FileNotFoundError):
                resolve_image(ep, "s09")


if __name__ == "__main__":
    unittest.main()
