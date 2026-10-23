"""QA — Bridge: mock default, real-mode opt-in gates, argv restriction, propagation."""
import os
import sys
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.bridge import (  # noqa: E402
    Bridge, MOCK, REAL, REAL_ALLOWED_TOOLS, REAL_PERMISSION_MODE)


class TestBridgeMock(unittest.TestCase):
    def test_default_mode_is_mock(self):
        b = Bridge()
        self.assertEqual(b.mode, MOCK)

    def test_mock_succeeds_not_connected(self):
        r = Bridge().execute({"command": "build", "target": "WF005"})
        self.assertEqual(r["mode"], "mock")
        self.assertEqual(r["status"], "SUCCEEDED")
        self.assertFalse(r["real_claude_connected"])     # mock is never "connected"
        self.assertTrue(r["result"]["validated"])

    def test_mock_bad_target_fails(self):
        r = Bridge().execute({"command": "build", "target": ""})
        self.assertEqual(r["status"], "FAILED")
        self.assertFalse(r["real_claude_connected"])


class TestBridgeRealGates(unittest.TestCase):
    def test_real_blocked_as_root(self):
        b = Bridge(mode=REAL, uid_getter=lambda: 0,
                   env={"AFFOS_STAGING_WORKSPACE": "/tmp", "AFFOS_CLAUDE_BIN": "/bin/true"})
        r = b.execute({"command": "build", "target": "ws1"})
        self.assertEqual(r["status"], "BLOCKED")
        self.assertIn("non-root", r["error"])
        self.assertFalse(r["real_claude_connected"])

    def test_real_blocked_without_workspace(self):
        b = Bridge(mode=REAL, uid_getter=lambda: 1000,
                   env={"AFFOS_CLAUDE_BIN": "/bin/true"})
        r = b.execute({"command": "build", "target": "ws1"})
        self.assertEqual(r["status"], "BLOCKED")
        self.assertIn("AFFOS_STAGING_WORKSPACE", r["error"])

    def test_real_blocked_without_cli(self):
        with tempfile.TemporaryDirectory() as d:
            b = Bridge(mode=REAL, uid_getter=lambda: 1000,
                       env={"AFFOS_STAGING_WORKSPACE": d})  # no AFFOS_CLAUDE_BIN, which() likely None
            b.claude_bin = None
            r = b.execute({"command": "build", "target": "ws1"})
            self.assertEqual(r["status"], "BLOCKED")
            self.assertIn("claude", r["error"].lower())

    def test_real_rejects_unsafe_target(self):
        with tempfile.TemporaryDirectory() as d:
            b = Bridge(mode=REAL, uid_getter=lambda: 1000,
                       env={"AFFOS_STAGING_WORKSPACE": d, "AFFOS_CLAUDE_BIN": "/bin/true"})
            r = b.execute({"command": "build", "target": "../etc/passwd"})
            self.assertEqual(r["status"], "FAILED")
            self.assertIn("invalid target", r["error"])


class TestBridgeRealWiring(unittest.TestCase):
    """Injected runner tests the WIRING only. real_claude_connected is set solely by a
    successful runner return — never by a test double claiming E2E success."""

    def _bridge(self, runner):
        with_dir = tempfile.mkdtemp()
        return Bridge(mode=REAL, uid_getter=lambda: 1000, runner=runner,
                      env={"AFFOS_STAGING_WORKSPACE": with_dir, "AFFOS_CLAUDE_BIN": "/opt/claude"}), with_dir

    def test_argv_is_read_only_restricted(self):
        seen = {}
        def runner(argv, cwd, timeout_s):
            seen["argv"] = argv; seen["cwd"] = cwd
            return {"returncode": 0, "stdout": '{"ok":true}', "stderr": ""}
        b, d = self._bridge(runner)
        b.execute({"command": "build", "target": "staging_ws"})
        argv = seen["argv"]
        self.assertEqual(argv[0], "/opt/claude")
        self.assertIn("--permission-mode", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], REAL_PERMISSION_MODE)
        i = argv.index("--allowedTools")
        self.assertEqual(argv[i + 1:i + 1 + len(REAL_ALLOWED_TOOLS)], REAL_ALLOWED_TOOLS)
        self.assertNotIn("Write", argv)
        self.assertNotIn("Edit", argv)
        self.assertNotIn("Bash", argv)
        self.assertEqual(seen["cwd"], d)                 # runs in the staging workspace

    def test_real_success_sets_connected(self):
        b, _ = self._bridge(lambda a, c, t: {"returncode": 0, "stdout": '{"dirs":[]}', "stderr": ""})
        r = b.execute({"command": "build", "target": "staging_ws"})
        self.assertEqual(r["status"], "SUCCEEDED")
        self.assertTrue(r["real_claude_connected"])      # only on real runner success
        self.assertIn("raw", r["result"])

    def test_real_failure_not_connected(self):
        b, _ = self._bridge(lambda a, c, t: {"returncode": 2, "stdout": "", "stderr": "boom"})
        r = b.execute({"command": "build", "target": "staging_ws"})
        self.assertEqual(r["status"], "FAILED")
        self.assertFalse(r["real_claude_connected"])
        self.assertIn("rc=2", r["error"])
        self.assertIn("boom", r["error"])

    def test_cli_is_error_in_stdout_is_failure(self):
        # CLI exits 0 but JSON says is_error (e.g. "Not logged in") → must be FAILED, not connected
        b, _ = self._bridge(lambda a, c, t: {"returncode": 0, "stderr": "",
                "stdout": '{"type":"result","is_error":true,"result":"Not logged in · Please run /login"}'})
        r = b.execute({"command": "build", "target": "staging_ws"})
        self.assertEqual(r["status"], "FAILED")
        self.assertFalse(r["real_claude_connected"])
        self.assertIn("Not logged in", r["error"])

    def test_output_is_capped(self):
        big = "x" * 100000
        b, _ = self._bridge(lambda a, c, t: {"returncode": 0, "stdout": big, "stderr": ""})
        b.output_limit = 100
        r = b.execute({"command": "build", "target": "staging_ws"})
        self.assertLessEqual(len(r["result"]["raw"]), 100)


if __name__ == "__main__":
    unittest.main()
