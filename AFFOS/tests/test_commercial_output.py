"""QA — AFFOS first commercial output (SPRINT 02). DRY-RUN; no prod credentials needed."""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors"))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
import commercial_output as co   # noqa: E402
import server                    # noqa: E402


class TestCommercialOutput(unittest.TestCase):
    def test_full_flow_shape_and_provenance(self):
        out = co.build_output({}, niche="home-living")
        self.assertEqual(out["status"], "DRY_RUN_OUTPUT")
        self.assertEqual(out["data_state"], "SEEDED")
        self.assertFalse(out["is_real"])                          # never REAL in DRY-RUN
        self.assertEqual(out["real_commerce_proof"], "NOT YET VERIFIED")
        for key in ("product", "offer", "commission", "campaign", "tracking_link",
                    "monetization", "source"):
            self.assertIn(key, out)
        # chain integrity
        self.assertTrue(out["tracking_link"])
        self.assertEqual(out["commission"]["rate"], out["offer"]["commission_rate"])
        exp = round(out["commission"]["reference_order_value"] * out["offer"]["commission_rate"], 2)
        self.assertEqual(out["commission"]["expected_on_reference_order"], exp)

    def test_niche_is_respected(self):
        out = co.build_output({}, niche="fitness")
        self.assertEqual(out["niche"], "fitness")
        self.assertIn("fitness", out["campaign"]["name"])

    def test_refuses_live_repo(self):
        out = co.build_output({"DATABASE_URL": "postgresql://x"})
        self.assertEqual(out["status"], "REFUSED")               # DRY-RUN only this sprint
        self.assertEqual(out["real_commerce_proof"], "NOT YET VERIFIED")

    def test_server_output_endpoint_dry_run(self):
        code, body = server.build_output_response({})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["status"], "DRY_RUN_OUTPUT")

    def test_server_output_endpoint_refuses_live(self):
        code, body = server.build_output_response({"DATABASE_URL": "postgresql://x"})
        self.assertEqual(code, 409)
        self.assertEqual(json.loads(body)["status"], "REFUSED")


if __name__ == "__main__":
    unittest.main()
