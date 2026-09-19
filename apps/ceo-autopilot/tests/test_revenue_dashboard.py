"""QA — CEO Revenue Dashboard (PRD-010 F). File test mới; không đụng test cũ."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from revenue_dashboard import RevenueDashboard  # noqa: E402


class TestRevenueDashboard(unittest.TestCase):
    def test_all_widgets(self):
        d = RevenueDashboard().dashboard()
        for w in ("todays_revenue", "pipeline_value", "leads", "affiliate_clicks",
                  "content_queue", "publish_status", "ai_cost"):
            self.assertIn(w, d)

    def test_ai_cost_placeholder(self):
        self.assertEqual(RevenueDashboard().ai_cost_placeholder()["status"], "placeholder")

    def test_injected_values(self):
        d = RevenueDashboard(
            revenue_overview={"total": 500.0, "affiliate": 300.0, "lead": 200.0},
            pipeline_value=12000.0,
            leads=[{"id": 1}, {"id": 2}],
            affiliate_clicks=42,
        ).dashboard()
        self.assertEqual(d["todays_revenue"]["total"], 500.0)
        self.assertEqual(d["pipeline_value"], 12000.0)
        self.assertEqual(d["leads"], 2)
        self.assertEqual(d["affiliate_clicks"], 42)


if __name__ == "__main__":
    unittest.main()
