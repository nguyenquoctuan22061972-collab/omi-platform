"""QA — AFFOS KPI Query Foundation (WP-D05-01). READ-ONLY aggregation.

Covers: recognized-revenue = production-verified only (D4), Impact counted (D2+D4 consequence),
refund reverses once, LIVE/SEEDED reported separately, Margin N/A on zero denominator (D3),
mixed-currency never collapsed, invalid provenance reported, pending excluded, ROI/Cash DEFERRED,
and an end-to-end run on the real SQLite TEST adapter.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))

from kpi import query          # noqa: E402
from data_access import Repo   # noqa: E402


def _row(amount, status, source, data_state, is_verified, currency="USD", srid="S1"):
    return {"amount": amount, "status": status, "currency": currency, "source": source,
            "source_record_id": srid, "data_state": data_state, "is_verified": is_verified}


class StubRepo:
    """Duck-typed repo returning canned commission rows (lets us inject PRODUCTION_VERIFIED rows
    that the SQLite TEST adapter intentionally forbids). SELECT-only interface."""
    def __init__(self, rows, ad=0.0):
        self._rows = rows
        self._ad = ad

    def query(self, sql, params=()):
        if "FROM commissions" in sql:
            return [dict(r) for r in self._rows]
        if "FROM expenses" in sql:
            return [{"s": self._ad}]
        raise AssertionError(f"unexpected SQL in KPI query: {sql}")


PROD_AWIN = _row(100.0, "APPROVED", "awin_production", "PRODUCTION_VERIFIED", 1, srid="A1")
PROD_IMPACT = _row(40.0, "CONFIRMED", "impact_production", "PRODUCTION_VERIFIED", 1, srid="I1")
PROD_REFUND = _row(20.0, "REFUNDED", "awin_production", "PRODUCTION_VERIFIED", 1, srid="A2")
LIVE_ROW = _row(50.0, "APPROVED", "awin", "LIVE", 0, srid="L1")
SEEDED_ROW = _row(30.0, "APPROVED", "seed", "SEEDED", 0, srid="SD1")
PROD_UNVERIFIED = _row(15.0, "APPROVED", "awin_production", "PRODUCTION_VERIFIED", 0, srid="A3")
PENDING_ROW = _row(999.0, "PENDING", "awin_production", "PRODUCTION_VERIFIED", 1, srid="A4")
INVALID_ROW = _row(77.0, "APPROVED", "", "PRODUCTION_VERIFIED", 1, srid="")
EUR_PROD = _row(10.0, "APPROVED", "awin_production", "PRODUCTION_VERIFIED", 1, currency="EUR", srid="E1")


class TestKpiQuery(unittest.TestCase):
    def test_recognized_only_production_verified(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN, LIVE_ROW, SEEDED_ROW]))
        self.assertEqual(k["recognized_revenue"], 100.0)   # only is_real counted
        self.assertEqual(k["unverified_revenue"], 50.0)    # LIVE reported separately
        self.assertEqual(k["simulated_revenue"], 30.0)     # SEEDED reported separately
        self.assertFalse(k["mixed_currency"])
        self.assertTrue(k["read_only"])

    def test_impact_production_is_counted(self):
        # D2+D4 accepted consequence: Impact is a PRODUCTION_SOURCE on this baseline -> counted.
        k = query.financial_kpis(StubRepo([PROD_AWIN, PROD_IMPACT]))
        self.assertEqual(k["recognized_revenue"], 140.0)

    def test_refund_reverses_once(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN, PROD_IMPACT, PROD_REFUND]))
        self.assertEqual(k["recognized_revenue"], 120.0)   # 100 + 40 - 20

    def test_margin_na_when_recognized_zero(self):
        k = query.financial_kpis(StubRepo([LIVE_ROW, SEEDED_ROW]))
        self.assertEqual(k["recognized_revenue"], 0.0)
        self.assertEqual(k["margin"], "N/A")               # D3: never 0.0

    def test_net_profit_and_margin_with_cost(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN]), ai_cost=30.0)
        self.assertEqual(k["net_profit"], 70.0)            # 100 - 30
        self.assertEqual(k["margin"], 0.7)

    def test_mixed_currency_never_collapsed(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN, EUR_PROD]))
        self.assertTrue(k["mixed_currency"])
        self.assertIsNone(k["revenue"])
        self.assertEqual(k["by_currency_recognized"], {"USD": 100.0, "EUR": 10.0})

    def test_invalid_provenance_reported_not_summed(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN, INVALID_ROW]))
        self.assertEqual(k["recognized_revenue"], 100.0)
        self.assertEqual(k["invalid_provenance_count"], 1)

    def test_pending_excluded(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN, PENDING_ROW]))
        self.assertEqual(k["recognized_revenue"], 100.0)

    def test_production_labelled_but_unverified_not_recognized(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN, PROD_UNVERIFIED]))
        self.assertEqual(k["recognized_revenue"], 100.0)   # is_verified=0 -> not is_real
        self.assertEqual(k["unverified_revenue"], 15.0)

    def test_deferred_metrics_not_computed(self):
        k = query.financial_kpis(StubRepo([PROD_AWIN]))
        self.assertIsNone(k["roi"])
        self.assertIsNone(k["cash"])
        self.assertIsNone(k["net_cash_flow"])

    def test_end_to_end_real_sqlite_test_adapter(self):
        # The SQLite adapter only allows TEST/DRY_RUN/SEEDED, so recognized revenue MUST be 0 and
        # the data is reported as simulated — a correct, honest result on non-production data.
        repo = Repo(data_state="TEST")
        repo.insert("commissions", {"id": "CO-1", "conversion_event_id": "CV-1", "amount": 30.0,
                    "status": "approved", "source": "seed", "source_record_id": "X1",
                    "data_state": "TEST", "currency": "USD", "fetched_at": "t", "is_verified": 0})
        k = query.financial_kpis(repo)
        self.assertEqual(k["recognized_revenue"], 0.0)
        self.assertEqual(k["simulated_revenue"], 30.0)
        self.assertEqual(k["margin"], "N/A")
        self.assertTrue(k["read_only"])


if __name__ == "__main__":
    unittest.main()
