"""QA — Execution Sandbox (PRD-014 B)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.execution import ExecutionContext  # noqa: E402
from orchestrator.runtime.sandbox import ExecutionSandbox, SandboxPolicy  # noqa: E402


class TestSandbox(unittest.TestCase):
    def test_allow_ok(self):
        sb = ExecutionSandbox(policy=SandboxPolicy(allow={"cap.ok"}))
        r = sb.run(ExecutionContext("cap.ok"), lambda c: "fine")
        self.assertTrue(r.ok)

    def test_blocked_not_allowed(self):
        sb = ExecutionSandbox(policy=SandboxPolicy(allow={"cap.ok"}))
        r = sb.run(ExecutionContext("cap.evil"), lambda c: "x")
        self.assertTrue(r.blocked)
        self.assertIn("allowlist", r.violation)

    def test_dry_run(self):
        sb = ExecutionSandbox(policy=SandboxPolicy(dry_run=True))
        called = {"n": 0}
        def h(c): called["n"] += 1; return "real"
        r = sb.run(ExecutionContext("cap.any"), h)
        self.assertTrue(r.ok)
        self.assertEqual(called["n"], 0)   # không chạy handler thật

    def test_output_limit(self):
        sb = ExecutionSandbox(policy=SandboxPolicy(max_output_bytes=10))
        r = sb.run(ExecutionContext("cap.big"), lambda c: "x" * 1000)
        self.assertFalse(r.ok)
        self.assertIn("vượt giới hạn", r.result.error)


if __name__ == "__main__":
    unittest.main()
