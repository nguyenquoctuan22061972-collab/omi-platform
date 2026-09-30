"""QA — AWIN LIVE chain scaffold. Fake transport chứng minh wiring; NEVER mints REAL."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))
import provenance, proof                 # noqa: E402
from data_access import Repo             # noqa: E402
from awin_live import AwinLiveClient, Transport, ProductionTransport  # noqa: E402


class FakeTransport(Transport):
    is_production = False   # test → KHÔNG BAO GIỜ real
    def get(self, url, token):
        if "programmes" in url:
            return {"programmes": [{"id": 111, "commissionRate": 0.07}]}
        if "transactions" in url:
            return {"transactions": [{"id": 900, "advertiserId": 111,
                    "saleAmount": {"amount": 1000000}, "commissionAmount": {"amount": 70000},
                    "commissionStatus": "confirmed", "transactionDate": "2026-09-30", "clickDate": "2026-09-29"}]}
        return {}


class TestAwinLive(unittest.TestCase):
    def test_blocked_without_credentials(self):
        c = AwinLiveClient({})
        self.assertFalse(c.auth()["ok"])
        self.assertIn("AWIN_API_TOKEN", c.auth()["blocked"])
        self.assertFalse(c.publisher_verify()["ok"])

    def test_deep_link_builder(self):
        c = AwinLiveClient({"AWIN_PUBLISHER_ID": "555"})
        dl = c.deep_link("111", "https://shop.example/p/1", "camp1")
        self.assertIn("awinmid=111", dl)
        self.assertIn("awinaffid=555", dl)
        self.assertIn("clickref=camp1", dl)
        self.assertIn("ued=", dl)

    def test_fake_transport_wiring_but_not_real(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinLiveClient(env, transport=FakeTransport())
        self.assertTrue(c.auth()["ok"])                 # có token + transport
        offers = c.get_offers()
        self.assertTrue(offers["ok"])
        # data_state phải là TEST (transport không production) → KHÔNG real
        self.assertEqual(offers["offers"][0]["data_state"], "TEST")
        repo = Repo(data_state="TEST")
        ing = c.ingest_transactions(repo, "2026-09-01", "2026-09-30")
        self.assertEqual(ing["ingested"], 1)
        self.assertEqual(ing["data_state"], "TEST")
        # proof phải NOT YET VERIFIED, is_real False
        pr = proof.real_commerce_proof(repo)
        self.assertEqual(pr["status"], "NOT YET VERIFIED")
        comm = repo.query("SELECT * FROM commissions")[0]
        self.assertFalse(provenance.is_real(comm))

    def test_production_transport_flag(self):
        self.assertTrue(ProductionTransport.is_production)
        # chỉ production transport + creds mới cho PRODUCTION_VERIFIED
        c = AwinLiveClient({"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "5"}, transport=ProductionTransport())
        self.assertEqual(c._state(), "PRODUCTION_VERIFIED")
        self.assertEqual(c.chain_status()["data_state"], "PRODUCTION_VERIFIED")

    def test_chain_status_blocked(self):
        st = AwinLiveClient({}).chain_status()
        self.assertFalse(st["ready_for_real"])
        self.assertEqual(len(st["steps"]), 9)


if __name__ == "__main__":
    unittest.main()
