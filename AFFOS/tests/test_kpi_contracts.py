"""QA — AFFOS KPI Contracts (WP-D05-01). Pure spec; asserts no vocabulary drift, correct statuses."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))

from kpi import contracts  # noqa: E402
import provenance          # noqa: E402


class TestKpiContracts(unittest.TestCase):
    def test_active_and_deferred_sets(self):
        active = set(contracts.active_ids())
        deferred = set(contracts.deferred_ids())
        self.assertIn("recognized_revenue", active)
        self.assertIn("total_cost", active)
        self.assertIn("net_profit", active)
        self.assertIn("margin", active)
        # ROI, Cash, Net Cash Flow are DEFERRED (never computed in WP-D05-01).
        self.assertEqual(deferred, {"roi", "cash", "net_cash_flow"})
        self.assertFalse(active & deferred)

    def test_recognized_revenue_is_production_verified_only(self):
        c = contracts.get("recognized_revenue")
        self.assertIn("is_real", c["formula"])
        self.assertIn("PRODUCTION_VERIFIED", c["data_state_rule"])

    def test_margin_na_rule(self):
        self.assertIn("N/A", contracts.get("margin")["missing_data_rule"])
        self.assertEqual(contracts.NA, "N/A")

    def test_cash_and_net_cash_flow_deferred_to_wp_r02(self):
        for k in ("cash", "net_cash_flow"):
            self.assertEqual(contracts.get(k)["status"], contracts.DEFERRED)
            self.assertIn("WP-R02", contracts.get(k)["source"])

    def test_no_new_revenue_labels_or_data_states(self):
        # The module-level asserts already guard this; re-check explicitly here.
        self.assertEqual(provenance.REVENUE_LABELS,
                         {"PRODUCTION_REVENUE", "UNVERIFIED_REVENUE", "SIMULATED_REVENUE"})
        self.assertEqual(provenance.DATA_STATES,
                         ["TEST", "DRY_RUN", "SEEDED", "LIVE", "PRODUCTION_VERIFIED"])

    def test_unknown_kpi_raises(self):
        with self.assertRaises(KeyError):
            contracts.get("does_not_exist")


if __name__ == "__main__":
    unittest.main()
