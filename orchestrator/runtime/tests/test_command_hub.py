"""QA — CommandHub: Console→Queue→Worker→ResultStore seam, correlation id, retry/idempotency."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.command_hub import CommandHub, CAPABILITY  # noqa: E402
from orchestrator.runtime import result_store as rs  # noqa: E402


class TestCommandHub(unittest.TestCase):
    def test_submit_sets_queued_with_ids(self):
        h = CommandHub()
        sub = h.submit("build", "WF005")
        self.assertEqual(sub["status"], "QUEUED")
        self.assertTrue(sub["task_id"].startswith("AFFOS-EXEC-"))
        self.assertTrue(sub["correlation_id"].startswith("cor_"))
        self.assertEqual(h.result(sub["correlation_id"])["status"], "QUEUED")

    def test_full_path_succeeds_and_persists(self):
        h = CommandHub()
        out = h.run("build", "WF005")
        self.assertEqual(out["status"], "SUCCEEDED")
        rec = h.result(out["correlation_id"])
        self.assertEqual(rec["status"], "SUCCEEDED")
        self.assertEqual(rec["correlation_id"], out["correlation_id"])   # id threaded through
        self.assertEqual(rec["worker"], "builder-01")
        self.assertEqual(rec["capability"], CAPABILITY)
        self.assertTrue(rec["result"]["validated"])
        self.assertEqual(rec["result"]["target"], "WF005")

    def test_failure_persisted_as_failed(self):
        h = CommandHub()
        out = h.run("build", "")            # empty target → handler raises
        self.assertEqual(out["status"], "FAILED")
        rec = h.result(out["correlation_id"])
        self.assertEqual(rec["status"], "FAILED")
        self.assertIn("target required", rec["error"])

    def test_blocked_when_command_not_executable(self):
        h = CommandHub()
        sub = h.submit("deploy", "x")       # deploy not in ALLOWED_COMMANDS
        self.assertEqual(sub["status"], "BLOCKED")
        self.assertEqual(h.result(sub["correlation_id"])["status"], "BLOCKED")

    def test_idempotent_same_correlation_id_single_row(self):
        h = CommandHub()
        cid = "cor_fixed_1"
        h.run("build", "WF001", correlation_id=cid)
        h.run("build", "WF001", correlation_id=cid)   # re-run same id
        rows = [r for r in [h.result(cid)] if r]
        self.assertEqual(h.store.count(), 1)           # no duplicate
        self.assertEqual(rows[0]["status"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
