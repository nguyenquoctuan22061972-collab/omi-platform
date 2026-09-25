"""QA — CEO Console Command API + Health Monitor (ZP-001). Pure route dispatch, no socket."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from console_api import Console  # noqa: E402
import health_monitor            # noqa: E402


class TestConsole(unittest.TestCase):
    def test_status(self):
        code, d = Console({}).route("GET", "/status")
        self.assertEqual(code, 200)
        self.assertTrue(d["ok"])
        self.assertIn("agents", d["os"])
        self.assertIn("health", d)

    def test_report_one_page(self):
        code, d = Console({}).route("GET", "/report")
        self.assertEqual(code, 200)
        self.assertEqual(d["title"], "OMI Executive Report")
        self.assertIn("qa", d)

    def test_health_route(self):
        code, d = Console({}).route("GET", "/health")
        self.assertEqual(code, 200)
        self.assertIn("compat", d["health"])

    def test_commands_dry_run(self):
        c = Console({})
        for cmd in ("build", "fix", "deploy"):
            code, d = c.route("POST", "/" + cmd, {}, {"target": "WF005"})
            self.assertEqual(code, 200)
            self.assertEqual(d["mode"], "plan")
        # deploy declares external permission
        _, dep = c.route("POST", "/deploy", {}, {"target": "x"})
        self.assertIn("PR-002", dep["requires_permission"])

    def test_auth_required_when_token_set(self):
        c = Console({"CONSOLE_TOKEN": "sekret"})
        code, _ = c.route("POST", "/build", {}, {"target": "x"})
        self.assertEqual(code, 401)
        code2, _ = c.route("POST", "/build", {"X-Console-Token": "sekret"}, {"target": "x"})
        self.assertEqual(code2, 200)

    def test_unknown_route(self):
        code, _ = Console({}).route("GET", "/nope")
        self.assertEqual(code, 404)

    def test_health_monitor_snapshot(self):
        s = health_monitor.snapshot({})
        self.assertIn("compat", s)
        self.assertEqual(s["live_probe"], "requires_vps")
        self.assertIn("crm-core", s["expected_services"])


if __name__ == "__main__":
    unittest.main()
