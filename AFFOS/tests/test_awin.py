"""QA — AWIN connector (PRD-017) + pipeline integration."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))
from data_access import Repo          # noqa: E402
from awin_connector import AwinConnector   # noqa: E402
import pipeline                       # noqa: E402


class TestAwin(unittest.TestCase):
    def test_dry_run_offers_and_ingest(self):
        r = Repo(); res = AwinConnector({}).ingest(r)
        self.assertEqual(res["mode"], "dry-run")
        self.assertEqual(r.count("offers"), 2)

    def test_live_gated(self):
        c = AwinConnector({"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "123"})
        self.assertTrue(c.is_live())
        self.assertEqual(c.fetch_offers()["mode"], "live_pending")
        self.assertIn("123", c.endpoints()["transactions"])

    def test_endpoints_no_secret(self):
        eps = AwinConnector({}).endpoints()
        self.assertTrue(eps["base"].startswith("https://api.awin.com"))

    def test_pipeline_with_awin_connector(self):
        r = pipeline.run(connector=AwinConnector({}), costs={"ai_cost": 2.0})
        self.assertEqual(r["data_source"], "dry-run")
        # AWIN seed: PROG-1 (1.5M+2.3M)*0.07=266000 ; PROG-2 640k*0.05=32000 => 298000
        self.assertEqual(r["totals"]["revenue"], 298000.0)
        self.assertEqual(r["totals"]["contribution_profit"], 298000.0 - 2.0)
        self.assertIn("C-AWIN-PROG-1", r["per_campaign"])
        self.assertEqual(r["per_campaign"]["C-AWIN-PROG-1"]["clicks"], 120)


if __name__ == "__main__":
    unittest.main()
