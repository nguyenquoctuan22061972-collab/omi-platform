"""QA — HeartRise EP01 storyboard (dữ liệu kịch bản). Thuần stdlib, luôn chạy được."""
import os
import sys
import unittest

# thư mục episode (chứa storyboard.py) — content-factory có gạch ngang nên nạp theo path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import storyboard as sb  # noqa: E402


class TestStoryboard(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(sb.EPISODE_ID, "heartrise_ep01")
        self.assertEqual(sb.HANDLE, "@HeartRiseStories")
        self.assertEqual(sb.CHANNEL, "HeartRise Stories")

    def test_has_narrative_arc(self):
        keys = [s.key for s in sb.STORYBOARD]
        self.assertEqual(keys[0], "intro")
        self.assertEqual(keys[-1], "outro")
        self.assertGreaterEqual(len(keys), 6)
        self.assertEqual(len(keys), len(set(keys)), "key cảnh phải duy nhất")

    def test_every_scene_valid(self):
        for s in sb.STORYBOARD:
            self.assertGreater(s.duration, 0)
            self.assertIn(s.kind, {"intro", "story", "quote", "outro"})
            self.assertIn(s.zoom, {"in", "out"})
            self.assertIn(s.align, {"center", "bottom"})
            self.assertTrue(s.title, f"cảnh {s.key} thiếu title")
            self.assertGreaterEqual(len(s.urls), 1, f"cảnh {s.key} không có nguồn ảnh")
            for u in s.urls:
                self.assertTrue(u.startswith("https://"))

    def test_multi_source_fallback_present(self):
        # ít nhất vài cảnh có >1 nguồn để fallback khi domain bị chặn
        multi = [s for s in sb.STORYBOARD if len(s.urls) >= 2]
        self.assertGreaterEqual(len(multi), 4)

    def test_runtime_reasonable(self):
        rt = sb.total_runtime()
        self.assertGreater(rt, 45)
        self.assertLess(rt, 120)

    def test_youtube_metadata_defined(self):
        self.assertTrue(sb.YT_TITLE)
        self.assertTrue(sb.YT_DESCRIPTION)
        self.assertGreaterEqual(len(sb.YT_TAGS), 3)


if __name__ == "__main__":
    unittest.main()
