"""QA — audit trail (PRD-008 C)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.audit import AuditTrail, MemorySink, EVENTS  # noqa: E402


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.sink = MemorySink()
        self.trail = AuditTrail(self.sink)

    def test_all_event_types(self):
        self.assertEqual(EVENTS, {"deploy", "login", "role_change",
                                  "workflow_activation", "adapter_enable", "rollback"})

    def test_record_each_event(self):
        for e in EVENTS:
            self.trail.record(e, actor="admin", target="x")
        self.assertEqual(len(self.sink.records), len(EVENTS))

    def test_invalid_event_raises(self):
        with self.assertRaises(ValueError):
            self.trail.record("hack")

    def test_secret_redacted(self):
        rec = self.trail.record("login", actor="admin", meta={"password": "p@ss", "ip": "1.2.3.4"})
        self.assertEqual(rec["meta"]["password"], "***redacted***")
        self.assertEqual(rec["meta"]["ip"], "1.2.3.4")

    def test_record_shape(self):
        rec = self.trail.record("deploy", actor="ci", target="v1.0")
        for k in ("id", "ts", "event", "actor", "target", "meta"):
            self.assertIn(k, rec)
        self.assertTrue(rec["id"].startswith("aud_"))


if __name__ == "__main__":
    unittest.main()
