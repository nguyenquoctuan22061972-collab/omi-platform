"""QA — Prompt Registry (PRD-009 B)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.prompts import PromptRegistry, CATEGORIES  # noqa: E402


class TestPrompts(unittest.TestCase):
    def setUp(self):
        self.r = PromptRegistry()

    def test_eight_categories(self):
        self.assertEqual(set(CATEGORIES), {
            "youtube_long", "shorts", "tiktok", "facebook", "seo", "thumbnail", "veo3", "vertex"})
        for c in CATEGORIES:
            self.assertEqual(self.r.latest_version(c), 1)

    def test_versioning(self):
        v = self.r.add_version("shorts", "new shorts v2 {topic}")
        self.assertEqual(v, 2)
        self.assertEqual(self.r.latest_version("shorts"), 2)
        self.assertIn("v2", self.r.get("shorts", 2))
        self.assertNotIn("v2", self.r.get("shorts", 1))

    def test_render(self):
        out = self.r.render("seo", topic="OMI Platform")
        self.assertIn("OMI Platform", out)

    def test_invalid_category(self):
        with self.assertRaises(KeyError):
            self.r.get("nope")

    def test_invalid_version(self):
        with self.assertRaises(IndexError):
            self.r.get("tiktok", 99)


if __name__ == "__main__":
    unittest.main()
