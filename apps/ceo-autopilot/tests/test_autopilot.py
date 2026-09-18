"""QA — CEO Autopilot integration layer (PRD-009 F)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from autopilot import CEOAutopilot  # noqa: E402


class TestAutopilot(unittest.TestCase):
    def test_dashboard_has_all_widgets(self):
        d = CEOAutopilot().dashboard()
        for w in ("morning_brief", "daily_priorities", "workflow_health",
                  "revenue", "ai_queue", "alerts", "approval_center"):
            self.assertIn(w, d)

    def test_revenue_is_placeholder(self):
        self.assertEqual(CEOAutopilot().revenue_placeholder()["status"], "placeholder")

    def test_morning_brief_uses_kpi(self):
        a = CEOAutopilot(kpi={"total_contacts": 10, "total_messages": 50, "win_rate": 0.4})
        mb = a.morning_brief()
        self.assertEqual(mb["contacts"], 10)
        self.assertEqual(mb["win_rate"], 0.4)

    def test_priorities_reflect_workload(self):
        a = CEOAutopilot(alerts=[{"x": 1}], approvals=[{"y": 1}],
                         queue_stats={"dead_letter": 2})
        pri = a.daily_priorities()
        self.assertTrue(any("approval" in p for p in pri))
        self.assertTrue(any("alert" in p for p in pri))
        self.assertTrue(any("dead-letter" in p for p in pri))

    def test_priorities_default(self):
        self.assertTrue(CEOAutopilot().daily_priorities())

    def test_workflow_health_counts(self):
        a = CEOAutopilot(workflow_status=[
            {"activation": "importable"}, {"activation": "importable"},
            {"activation": "planned", "planned": True}])
        wh = a.workflow_health()
        self.assertEqual(wh["ready"], 2)
        self.assertEqual(wh["planned"], 1)


if __name__ == "__main__":
    unittest.main()
