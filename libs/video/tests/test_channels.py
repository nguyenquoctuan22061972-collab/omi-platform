"""QA — registry 10 kênh."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.video import CHANNELS, get_channel, list_keys  # noqa: E402


class TestChannels(unittest.TestCase):
    def test_ten_channels(self):
        self.assertEqual(len(CHANNELS), 10)
        self.assertEqual(len(set(list_keys())), 10)

    def test_known_keys_and_handles(self):
        self.assertEqual(get_channel("heartrise").handle, "@HeartRiseStories")
        self.assertEqual(get_channel("finance").brand, "FinanceFreedomPro")
        self.assertEqual(get_channel("mystery").handle, "@WorldMysteriesDaily")

    def test_case_insensitive_lookup(self):
        self.assertIs(get_channel("FINANCE"), get_channel("finance"))

    def test_unknown_raises(self):
        with self.assertRaises(KeyError):
            get_channel("nope")

    def test_every_channel_valid(self):
        seen_handles = set()
        for c in CHANNELS:
            self.assertTrue(c.brand and c.handle.startswith("@"))
            self.assertEqual(len(c.accent), 3)
            self.assertTrue(all(0 <= v <= 255 for v in c.accent))
            self.assertIn(c.yt_category, {"finance", "tech", "inspire", "default"})
            self.assertNotIn(c.handle, seen_handles, "handle phải duy nhất")
            seen_handles.add(c.handle)


if __name__ == "__main__":
    unittest.main()
