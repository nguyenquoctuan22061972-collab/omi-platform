"""QA — ResultStore: persist, idempotency, status, secret scrub."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime import result_store as rs  # noqa: E402


class TestResultStore(unittest.TestCase):
    def test_put_get_roundtrip(self):
        s = rs.ResultStore()
        s.put({"correlation_id": "cor_1", "task_id": "T1", "command": "build",
               "target": "WF005", "status": rs.QUEUED})
        r = s.get("cor_1")
        self.assertEqual(r["status"], "QUEUED")
        self.assertEqual(r["task_id"], "T1")
        self.assertEqual(r["target"], "WF005")

    def test_idempotent_upsert_no_duplicate(self):
        s = rs.ResultStore()
        for st in (rs.QUEUED, rs.RUNNING, rs.SUCCEEDED):
            s.put({"correlation_id": "cor_X", "task_id": "T", "command": "build",
                   "target": "x", "status": st,
                   "result": {"ok": True} if st == rs.SUCCEEDED else None})
        self.assertEqual(s.count(), 1)                 # same correlation_id → 1 row
        r = s.get("cor_X")
        self.assertEqual(r["status"], "SUCCEEDED")
        self.assertEqual(r["result"], {"ok": True})
        self.assertEqual(r["command"], "build")        # earlier fields preserved

    def test_created_at_preserved_updated_changes(self):
        s = rs.ResultStore()
        a = s.put({"correlation_id": "c", "status": rs.QUEUED})
        b = s.put({"correlation_id": "c", "status": rs.SUCCEEDED, "result": {"n": 1}})
        self.assertEqual(a["created_at"], b["created_at"])

    def test_invalid_status_rejected(self):
        s = rs.ResultStore()
        with self.assertRaises(ValueError):
            s.put({"correlation_id": "c", "status": "WAT"})

    def test_missing_correlation_id_rejected(self):
        s = rs.ResultStore()
        with self.assertRaises(ValueError):
            s.put({"status": rs.QUEUED})

    def test_error_is_scrubbed(self):
        s = rs.ResultStore()
        leak = "boom token=SUPER_SEKRET_123 and eyJabc.def.ghi tail"
        s.put({"correlation_id": "c", "status": rs.FAILED, "error": leak})
        err = s.get("c")["error"]
        self.assertNotIn("SUPER_SEKRET_123", err)
        self.assertNotIn("eyJabc.def.ghi", err)
        self.assertIn("boom", err)

    def test_get_missing_returns_none(self):
        self.assertIsNone(rs.ResultStore().get("nope"))


if __name__ == "__main__":
    unittest.main()
