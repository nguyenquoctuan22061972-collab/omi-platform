"""QA — Audit actions + retention (PRD-012 B)."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.audit.retention import ActionLog, RetentionPolicy, ACTIONS  # noqa: E402


class TestRetention(unittest.TestCase):
    def test_actions_cover_required(self):
        for a in ("login", "workflow_trigger", "publish", "rollback"):
            self.assertIn(a, ACTIONS)

    def test_record_each(self):
        log = ActionLog()
        for a in ("login", "workflow_trigger", "publish", "rollback"):
            log.record(a, actor="admin", target="x")
        self.assertEqual(len(log.records), 4)
        self.assertEqual(len(log.by_action("publish")), 1)

    def test_invalid_action(self):
        with self.assertRaises(ValueError):
            ActionLog().record("hack")

    def test_secret_redacted(self):
        rec = ActionLog().record("login", meta={"password": "p", "ip": "1.1.1.1"})
        self.assertEqual(rec["meta"]["password"], "***redacted***")
        self.assertEqual(rec["meta"]["ip"], "1.1.1.1")

    def test_retention_prunes_old(self):
        log = ActionLog(RetentionPolicy(days=1))
        log.record("login")
        old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        log.records.insert(0, {"id": "x", "ts": old, "action": "login", "actor": "", "target": "", "meta": {}})
        log.record("logout")  # trigger prune
        self.assertTrue(all(r["ts"] >= log.policy.cutoff_iso() for r in log.records))


if __name__ == "__main__":
    unittest.main()
