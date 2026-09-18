"""QA — Adapter Activation (PRD-007 B). Không network; fail-safe + enable flag."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from libs.integrations import get_adapter  # noqa: E402
from libs.integrations import activation as act  # noqa: E402


class TestActivation(unittest.TestCase):
    def test_disabled_by_default(self):
        self.assertFalse(act.is_enabled("telegram", {}))

    def test_enabled_flag(self):
        self.assertTrue(act.is_enabled("telegram", {"TELEGRAM_ENABLED": "true"}))
        self.assertFalse(act.is_enabled("telegram", {"TELEGRAM_ENABLED": "no"}))

    def test_validate_env_reports_missing(self):
        a = get_adapter("telegram", env={})
        v = act.validate_env(a)
        self.assertFalse(v["configured"])
        self.assertIn("TELEGRAM_BOT_TOKEN", v["missing_env"])

    def test_connection_test_dry_run(self):
        env = {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        a = get_adapter("telegram", env=env)
        ct = act.connection_test(a, env)
        self.assertEqual(ct["mode"], "dry-run")
        self.assertTrue(ct["ok"])

    def test_safe_send_skips_when_disabled(self):
        a = get_adapter("telegram", env={"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"})
        res = act.safe_send(a, {"text": "hi"}, env={})  # ENABLED không set
        self.assertEqual(res["status"], "skipped")
        self.assertEqual(res["reason"], "disabled")

    def test_safe_send_skips_when_missing_env(self):
        env = {"TELEGRAM_ENABLED": "true"}
        a = get_adapter("telegram", env=env)
        res = act.safe_send(a, {"text": "hi"}, env=env)
        self.assertEqual(res["status"], "skipped")
        self.assertEqual(res["reason"], "missing_env")

    def test_safe_send_dry_run_when_ready(self):
        env = {"TELEGRAM_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}
        a = get_adapter("telegram", env=env)
        res = act.safe_send(a, {"text": "hi"}, env=env)
        self.assertEqual(res["status"], "dry-run")  # vẫn không gọi API thật

    def test_report_covers_six(self):
        rep = act.activation_report({})
        self.assertEqual(len(rep), 6)
        self.assertTrue(all(r["mode"] == "dry-run" for r in rep))


if __name__ == "__main__":
    unittest.main()
