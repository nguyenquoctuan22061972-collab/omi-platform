"""QA — Alert Engine (PRD-012 E)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.alerts import AlertEngine, ALERT_CHANNELS  # noqa: E402

TG_FULL = {"TELEGRAM_ALERT_ENABLED": "true", "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1"}


class TestAlerts(unittest.TestCase):
    def test_channels(self):
        self.assertEqual(set(ALERT_CHANNELS), {"telegram", "smtp"})

    def test_disabled_by_default(self):
        self.assertEqual(AlertEngine(env={}).send("telegram", "P1", "x")["status"], "skipped")

    def test_enabled_but_missing_env(self):
        res = AlertEngine(env={"TELEGRAM_ALERT_ENABLED": "true"}).send("telegram", "P1", "x")
        self.assertEqual(res["reason"], "missing_env")

    def test_enabled_configured_dry_run(self):
        res = AlertEngine(env=TG_FULL).send("telegram", "P1", "down!")
        self.assertEqual(res["status"], "dry-run")
        self.assertEqual(res["severity"], "P1")

    def test_unknown_channel(self):
        self.assertEqual(AlertEngine().send("sms", "P2", "x")["status"], "error")

    def test_broadcast(self):
        out = AlertEngine(env=TG_FULL).broadcast("P2", "warn")
        by = {r["channel"]: r["status"] for r in out}
        self.assertEqual(by["telegram"], "dry-run")
        self.assertEqual(by["smtp"], "skipped")


if __name__ == "__main__":
    unittest.main()
