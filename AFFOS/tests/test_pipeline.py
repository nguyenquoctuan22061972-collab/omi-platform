"""QA — AFFOS revenue pipeline (PRD-017): data access → attribution → economics → profit."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "core", "attribution"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "affiliate-network"))
from data_access import Repo, CHAIN_TABLES  # noqa: E402
import attribution                          # noqa: E402
from connector import AffiliateNetworkConnector  # noqa: E402
import pipeline                             # noqa: E402


class TestPipeline(unittest.TestCase):
    def test_repo_insert_query(self):
        r = Repo(); r.insert("products", {"id": "P1", "title": "x", "price": 100})
        self.assertEqual(r.count("products"), 1)
        with self.assertRaises(ValueError):
            r.insert("not_a_table", {"id": "x"})

    def test_connector_dry_run_ingest(self):
        r = Repo(); res = AffiliateNetworkConnector({}).ingest(r)
        self.assertEqual(res["mode"], "dry-run")
        self.assertEqual(r.count("offers"), 2)

    def test_connector_live_gated(self):
        c = AffiliateNetworkConnector({"AFFILIATE_API_KEY": "k", "AFFILIATE_NETWORK_ID": "n"})
        self.assertTrue(c.is_live())
        self.assertEqual(c.fetch_offers()["mode"], "live_pending")  # cần gọi API thật -> chưa bật

    def test_full_pipeline_profit(self):
        r = pipeline.run(costs={"ai_cost": 5.2, "infrastructure_cost": 1})
        # MP-1: 2 conv * 4,990,000 * 0.10 = 998,000 ; MP-2: 1 * 890,000 * 0.08 = 71,200
        self.assertEqual(r["totals"]["revenue"], 1069200.0)
        self.assertEqual(r["totals"]["contribution_profit"], 1069200.0 - 6.2)
        self.assertEqual(r["counts"]["commissions"], 3)
        self.assertIn("C-MP-1", r["per_campaign"])
        self.assertEqual(r["per_campaign"]["C-MP-1"]["conversions"], 2)

    def test_attribution_epc_cr(self):
        r = pipeline.run()
        c1 = r["per_campaign"]["C-MP-1"]
        self.assertEqual(c1["clicks"], 50)
        self.assertAlmostEqual(c1["cr"], 2/50)
        self.assertGreater(c1["epc"], 0)


if __name__ == "__main__":
    unittest.main()
