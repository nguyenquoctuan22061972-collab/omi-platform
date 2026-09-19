"""QA — Revenue Engine (PRD-010 A + Step4)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from revenue import (  # noqa: E402
    RevenueRegistry, PayoutAbstraction, ConversionTracker,
    AffiliateClickPipeline, RevenueEventDispatcher,
)


class TestRevenue(unittest.TestCase):
    def test_registry_overview(self):
        r = RevenueRegistry()
        r.record("affiliate", 100, month="2026-09")
        r.record("lead", 50, month="2026-09")
        r.record("affiliate", 25, month="2026-10")
        ov = r.overview()
        self.assertEqual(ov["total"], 175.0)
        self.assertEqual(ov["affiliate"], 125.0)
        self.assertIsNone(ov["rpm_placeholder"])
        self.assertEqual(ov["monthly_trend"]["2026-09"], 150.0)
        self.assertEqual(ov["sources"]["lead"], 50.0)

    def test_payout_dry_run(self):
        p = PayoutAbstraction().request_payout(500, method="momo")
        self.assertEqual(p["status"], "dry-run")
        self.assertEqual(p["amount"], 500.0)

    def test_conversion_rate(self):
        c = ConversionTracker()
        c.track("clk1", 10)
        self.assertEqual(c.rate(4), 0.25)
        self.assertEqual(c.rate(0), 0.0)

    def test_click_pipeline(self):
        p = AffiliateClickPipeline()
        clk = p.record_click("shopee", campaign="c1")
        p.convert(clk["id"], 30.0)
        st = p.stats()
        self.assertEqual(st["clicks"], 1)
        self.assertEqual(st["conversions"], 1)
        self.assertEqual(st["cvr"], 1.0)

    def test_event_dispatcher(self):
        d = RevenueEventDispatcher()
        got = []
        d.subscribe(lambda e: got.append(e))
        ev = d.dispatch({"type": "revenue", "amount": 99})
        self.assertTrue(ev["dry_run"])
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["amount"], 99)


if __name__ == "__main__":
    unittest.main()
