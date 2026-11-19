"""QA — sinh .srt từ timeline cảnh."""
import os
import sys
import unittest
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.video import srt_from_scenes, scene_windows  # noqa: E402


@dataclass
class FakeScene:
    duration: float
    title: str = ""
    subtitle: str = ""


class TestWindows(unittest.TestCase):
    def test_tiling_sums_to_total(self):
        durs = [7.0, 9.0, 8.0]
        T = 0.8
        wins = scene_windows(durs, T)
        self.assertEqual(len(wins), 3)
        # tổng độ dài visible = sum(d) - (n-1)*T
        total = wins[-1][1]
        self.assertAlmostEqual(total, sum(durs) - 2 * T, places=3)
        # không chồng lấn, liền mạch
        for i in range(1, len(wins)):
            self.assertAlmostEqual(wins[i][0], wins[i - 1][1], places=3)

    def test_last_scene_full(self):
        wins = scene_windows([5.0, 5.0], 1.0)
        self.assertAlmostEqual(wins[0][1] - wins[0][0], 4.0, places=3)  # 5-1
        self.assertAlmostEqual(wins[1][1] - wins[1][0], 5.0, places=3)  # full


class TestSrt(unittest.TestCase):
    def test_format_and_count(self):
        scenes = [FakeScene(6, "Dòng một", "phụ đề một"),
                  FakeScene(6, "“Trích dẫn”", "")]
        srt = srt_from_scenes(scenes, 0.8)
        self.assertIn("1\n00:00:00,000 --> ", srt)
        self.assertIn("-->", srt)
        self.assertIn("Dòng một", srt)
        self.assertIn("phụ đề một", srt)
        self.assertNotIn("“", srt)  # bỏ ngoặc trang trí
        # 2 cue
        self.assertEqual(srt.count("-->"), 2)

    def test_empty_text_skipped(self):
        scenes = [FakeScene(5, "", ""), FakeScene(5, "Có chữ", "")]
        srt = srt_from_scenes(scenes, 0.5)
        self.assertEqual(srt.count("-->"), 1)


if __name__ == "__main__":
    unittest.main()
