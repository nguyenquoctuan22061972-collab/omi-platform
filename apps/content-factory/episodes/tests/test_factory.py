"""QA — episode factory: lập kế hoạch cảnh + script (không render, không mạng)."""
import os
import sys
import unittest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, ".."))                    # episodes/
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", ".."))  # repo root
import factory  # noqa: E402
import script  # noqa: E402


class TestScenePlan(unittest.TestCase):
    def test_template_channel_plan(self):
        req = factory.EpisodeRequest("finance", 1, "")
        plan, title, yt_title, yt_desc, yt_tags = factory._scene_plan(
            req, factory.get_channel("finance"))
        self.assertGreaterEqual(len(plan), 6)
        self.assertIn("FinanceFreedomPro", yt_title)
        self.assertTrue(yt_tags)
        for urls, kw in plan:
            self.assertGreaterEqual(len(urls), 1)
            self.assertTrue(all(u.startswith("https://") for u in urls))
            self.assertIn(kw["kind"], {"intro", "story", "quote", "outro"})

    def test_heartrise_uses_bespoke(self):
        req = factory.EpisodeRequest("heartrise", 1, "")
        plan, title, *_ = factory._scene_plan(req, factory.get_channel("heartrise"))
        self.assertEqual(title, "Ngày Con Tim Thức Dậy")
        self.assertEqual(len(plan), 8)

    def test_theme_urls_cover_default_beats(self):
        beats = script.generate("B", "Finance", 1, "T")
        for b in beats:
            self.assertIn(b.theme, factory.THEME_URLS,
                          f"theme '{b.theme}' chưa có ảnh trong pool")


class TestScript(unittest.TestCase):
    def test_default_arc(self):
        beats = script.generate("B", "Health", 1, "Tiêu đề")
        keys = [b.key for b in beats]
        self.assertEqual(keys[0], "intro")
        self.assertEqual(keys[-1], "outro")

    def test_script_text_strips_decoration(self):
        beats = script.generate("B", "Health", 1, "T")
        txt = script.script_text(beats)
        self.assertNotIn("“", txt)
        self.assertNotIn("\n", txt)
        self.assertGreater(len(txt), 50)


if __name__ == "__main__":
    unittest.main()
