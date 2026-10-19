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

    # ---- command path wiring (execute → orchestrator → result store → receiver) ----
    def test_execute_build_runs_real_path_not_plan(self):
        c = Console({})
        code, d = c.route("POST", "/build", {}, {"target": "WF005", "execute": True})
        self.assertEqual(code, 200)
        self.assertEqual(d["mode"], "execute")        # NOT a plan
        self.assertEqual(d["status"], "SUCCEEDED")
        self.assertTrue(d["correlation_id"].startswith("cor_"))
        self.assertTrue(d["task_id"].startswith("AFFOS-EXEC-"))

    def test_end_to_end_via_real_entry_point(self):
        # one command through the real Console entry point, enqueued, worked, persisted,
        # then read back by the SAME correlation_id — no hand-wired harness.
        c = Console({})
        _, sub = c.route("POST", "/fix", {}, {"target": "WF007", "execute": True})
        cid = sub["correlation_id"]
        code, res = c.route("GET", "/result/" + cid, {})
        self.assertEqual(code, 200)
        self.assertEqual(res["correlation_id"], cid)       # same id round-trips
        self.assertEqual(res["status"], "SUCCEEDED")
        self.assertEqual(res["target"], "WF007")
        self.assertEqual(res["result"]["command"], "fix")

    def test_deploy_never_executes(self):
        c = Console({})
        _, d = c.route("POST", "/deploy", {}, {"target": "x", "execute": True})
        self.assertEqual(d["mode"], "plan")               # deploy stays plan-only
        self.assertIn("PR-002", d["requires_permission"])

    def test_result_unknown_correlation_id_404(self):
        code, d = Console({}).route("GET", "/result/cor_does_not_exist", {})
        self.assertEqual(code, 404)
        self.assertFalse(d["ok"])

    def test_result_requires_auth_when_token_set(self):
        c = Console({"CONSOLE_TOKEN": "sekret"})
        _, sub = c.route("POST", "/build", {"X-Console-Token": "sekret"},
                         {"target": "WF009", "execute": True})
        cid = sub["correlation_id"]
        code_no, _ = c.route("GET", "/result/" + cid, {})                       # no token
        self.assertEqual(code_no, 401)
        code_ok, res = c.route("GET", "/result/" + cid, {"X-Console-Token": "sekret"})
        self.assertEqual(code_ok, 200)
        self.assertEqual(res["status"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
