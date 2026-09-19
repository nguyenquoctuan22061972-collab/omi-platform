"""QA — Execution Engine (PRD-013 A)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import time  # noqa: E402
import unittest  # noqa: E402
from libs.metrics import MockProvider  # noqa: E402
from libs.audit import AuditTrail, MemorySink  # noqa: E402
from orchestrator.runtime.execution import (  # noqa: E402
    ExecutionContext, ExecutionEngine, ExecutionResult, ExecutionState, AUDIT_EVENTS)


class TestExecution(unittest.TestCase):
    def test_success_with_metrics_and_audit(self):
        m = MockProvider(); sink = MemorySink()
        eng = ExecutionEngine(metrics=m, audit=AuditTrail(sink, extra_events=AUDIT_EVENTS))
        ctx = ExecutionContext("cap.echo", {"x": 1})
        res = eng.run(ctx, lambda c: c.payload["x"] + 1)
        self.assertTrue(res.ok)
        self.assertEqual(res.state, ExecutionState.SUCCEEDED)
        self.assertEqual(res.output, 2)
        self.assertEqual(m.collect()["execution_success"], 1.0)
        events = [r["event"] for r in sink.records]
        self.assertIn("execution_start", events)
        self.assertIn("execution_success", events)

    def test_failure(self):
        m = MockProvider()
        eng = ExecutionEngine(metrics=m)
        def boom(c): raise ValueError("nope")
        res = eng.run(ExecutionContext("cap.boom"), boom)
        self.assertEqual(res.state, ExecutionState.FAILED)
        self.assertIn("ValueError", res.error)
        self.assertEqual(m.collect()["execution_failure"], 1.0)

    def test_timeout(self):
        eng = ExecutionEngine()
        ctx = ExecutionContext("cap.slow", timeout_s=0.05)
        res = eng.run(ctx, lambda c: time.sleep(2))
        self.assertEqual(res.state, ExecutionState.TIMED_OUT)
        self.assertTrue(ctx.cancel_token.cancelled)

    def test_cancel_before_run(self):
        eng = ExecutionEngine()
        ctx = ExecutionContext("cap.x"); ctx.cancel()
        res = eng.run(ctx, lambda c: "should-not-run")
        self.assertEqual(res.state, ExecutionState.CANCELLED)

    def test_state_terminal(self):
        self.assertTrue(ExecutionState.SUCCEEDED.is_terminal())
        self.assertFalse(ExecutionState.RUNNING.is_terminal())


if __name__ == "__main__":
    unittest.main()
