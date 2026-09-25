"""QA — WF005 hardening: runtime (idempotency/retry/rate-limit/observability), QA runner, compat."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from zalo_runtime import ZaloRuntime, RateLimiter   # noqa: E402
from qa_runner import QARunner                       # noqa: E402
import compat_check                                  # noqa: E402

EVENT = {"sender": {"id": "u1"}, "message": {"text": "báo giá Premium", "msg_id": "m-1"}}


class TestHardening(unittest.TestCase):
    def test_idempotency(self):
        rt = ZaloRuntime(env={})
        r1 = rt.process(EVENT)
        r2 = rt.process(EVENT)      # cùng msg_id → duplicate
        self.assertEqual(r1["status"], "ok")
        self.assertEqual(r2["status"], "duplicate")

    def test_rate_limit(self):
        t = {"v": 0.0}
        rl = RateLimiter(per_min=1, clock=lambda: t["v"])
        self.assertTrue(rl.allow())
        self.assertFalse(rl.allow())   # hết token trong cùng thời điểm

    def test_observability_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            rt = ZaloRuntime(env={}, log_path=os.path.join(d, "wf005.log"))
            rt.process(EVENT)
            snap = rt.snapshot()
            self.assertEqual(snap["success"], 1)
            self.assertTrue(os.path.isfile(os.path.join(d, "wf005.log")))

    def test_qa_runner_pass(self):
        r = QARunner().run_gates("WF005", [
            ("architecture", "chain", lambda: True),
            ("regression", "tests", lambda: True),
            ("security", "secret-scan", lambda: True),
            ("production_safety", "prod-untouched", lambda: True),
        ])
        self.assertTrue(r["passed"])

    def test_qa_runner_fail_triggers_rollback(self):
        qr = QARunner()
        flag = {"rolled": False}
        r = qr.run_gates("WF005", [
            ("architecture", "chain", lambda: True),
            ("regression", "tests", lambda: False),
        ], on_rollback=lambda: flag.__setitem__("rolled", True))
        self.assertFalse(r["passed"])
        self.assertEqual(r["failed_gate"], "regression")
        self.assertTrue(flag["rolled"])
        self.assertEqual(qr.rollback.last()["target"], "WF005")

    def test_compat_wf004_wf005(self):
        rep = compat_check.report(["WF004.n8n.json", "WF005.n8n.json"])
        self.assertTrue(rep["compatible"])
        for w in rep["workflows"]:
            self.assertTrue(w["all_builtin"])
            self.assertFalse(w["uses_env"])
        self.assertTrue(rep["infra"]["compose_present"])
        self.assertTrue(rep["infra"]["nginx_conf_present"])


if __name__ == "__main__":
    unittest.main()
