"""QA — Publish Connectors (PRD-009 G)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.publish import CONNECTORS, get_connector  # noqa: E402


class TestPublish(unittest.TestCase):
    def test_four_connectors(self):
        self.assertEqual(set(CONNECTORS), {"youtube", "tiktok", "facebook", "telegram"})

    def test_unconfigured_default(self):
        c = get_connector("youtube", env={})
        self.assertFalse(c.is_configured())

    def test_configured_from_env(self):
        c = get_connector("telegram", env={"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"})
        self.assertTrue(c.is_configured())

    def test_publish_is_dry_run(self):
        c = get_connector("tiktok", env={"TIKTOK_CLIENT_KEY": "k", "TIKTOK_CLIENT_SECRET": "s"})
        res = c.publish({"title": "Demo", "kind": "short"})
        self.assertEqual(res["status"], "dry-run")
        self.assertEqual(res["would_publish"]["title"], "Demo")

    def test_invalid_connector(self):
        with self.assertRaises(KeyError):
            get_connector("myspace")


if __name__ == "__main__":
    unittest.main()
