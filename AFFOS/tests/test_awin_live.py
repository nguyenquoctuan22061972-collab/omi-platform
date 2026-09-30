"""QA — AWIN LIVE adapter (PRD-017 / CTO AWIN LIVE IMPLEMENTATION).

Economic-truth proofs:
  - Fake transport chứng minh wiring nhưng NEVER mints REAL.
  - Production transport cần credentials, không dùng seed, lỗi ở dạng non-real.
  - Chỉ production transport + creds mới đạt PRODUCTION_VERIFIED; SQLite bị từ chối cho production.
  - Currency của production là bắt buộc (không mặc định VND).
Không có test nào gọi mạng thật hay bịa dữ liệu production là REAL.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))
import provenance, proof                 # noqa: E402
from data_access import Repo             # noqa: E402
from awin_live import (                  # noqa: E402
    AwinLiveClient, Transport, ProductionTransport,
    AwinError, AwinAuthError, AwinPermissionError, AwinHTTPError,
    AwinNetworkError, AwinCurrencyError, ProductionStorageError,
)


class FakeTransport(Transport):
    is_production = False   # test → KHÔNG BAO GIỜ real
    def get(self, url, token):
        if "programmes" in url:
            return {"programmes": [{"id": 111, "commissionRate": 0.07,
                                    "currencyCode": "USD"}]}
        if "transactions" in url:
            return {"transactions": [{"id": 900, "advertiserId": 111,
                    "saleAmount": {"amount": 1000000, "currency": "USD"},
                    "commissionAmount": {"amount": 70000, "currency": "USD"},
                    "commissionStatus": "confirmed", "transactionDate": "2026-09-30",
                    "clickDate": "2026-09-29"}]}
        return {}


class StubProduction(ProductionTransport):
    """Transport gắn cờ production (is_production=True) nhưng KHÔNG chạm mạng và
    KHÔNG có seed — dùng để chứng minh guard của nhánh production mà không hề
    persist bất kỳ record 'real' bịa đặt nào. Vẫn yêu cầu token như transport thật."""
    def __init__(self, raise_exc=None, payload=None):
        self.raise_exc = raise_exc
        self.payload = {} if payload is None else payload

    def get(self, url, token):
        if not token:
            raise AwinAuthError("missing token")
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.payload


class TestAwinLive(unittest.TestCase):
    # ---------- credential / wiring gates ----------
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

    def test_chain_status_blocked(self):
        st = AwinLiveClient({}).chain_status()
        self.assertFalse(st["ready_for_real"])
        self.assertEqual(len(st["steps"]), 9)

    def test_fake_transport_wiring_but_not_real(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinLiveClient(env, transport=FakeTransport())
        self.assertTrue(c.auth()["ok"])
        offers = c.get_offers()
        self.assertTrue(offers["ok"])
        self.assertEqual(offers["offers"][0]["data_state"], "TEST")
        repo = Repo(data_state="TEST")
        ing = c.ingest_transactions(repo, "2026-09-01", "2026-09-30")
        self.assertEqual(ing["ingested"], 1)
        self.assertEqual(ing["data_state"], "TEST")
        pr = proof.real_commerce_proof(repo)
        self.assertEqual(pr["status"], "NOT YET VERIFIED")
        comm = repo.query("SELECT * FROM commissions")[0]
        self.assertFalse(provenance.is_real(comm))

    # ---------- CTO required proof #1: fake transport can NEVER become production ----------
    def test_fake_transport_never_production(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinLiveClient(env, transport=FakeTransport())
        self.assertFalse(c._is_production())
        self.assertEqual(c._state(), "TEST")             # đủ creds vẫn TEST
        self.assertEqual(c._source(), "awin_fake_test")
        for o in c.get_offers()["offers"]:
            self.assertFalse(provenance.is_real(o))       # KHÔNG BAO GIỜ real

    # ---------- CTO required proof #2: production transport requires credentials ----------
    def test_production_requires_credentials(self):
        c = AwinLiveClient({"AWIN_PUBLISHER_ID": "5"}, transport=ProductionTransport())
        self.assertFalse(c.auth()["ok"])
        self.assertIn("AWIN_API_TOKEN", c.auth()["blocked"])
        self.assertNotEqual(c._state(), "PRODUCTION_VERIFIED")
        self.assertFalse(c.get_offers()["ok"])            # bị chặn, không gọi mạng
        with self.assertRaises(AwinAuthError):            # transport thật cũng raise
            ProductionTransport().get("https://api.awin.com/x", "")

    # ---------- CTO required proof #3: production transport does NOT use seed data ----------
    def test_production_never_returns_seed(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinLiveClient(env, transport=StubProduction(raise_exc=AwinNetworkError("no egress")))
        with self.assertRaises(AwinNetworkError):         # thất bại minh bạch, KHÔNG fallback seed
            c.get_offers()
        import inspect, awin_live
        src = inspect.getsource(awin_live.ProductionTransport)
        self.assertIn("urllib", src)                      # transport thật đi mạng
        self.assertNotIn("programmes", src)               # không nhúng seed offer
        self.assertNotIn("saleAmount", src)               # không nhúng seed transaction

    # ---------- CTO required proof #4: HTTP/auth errors remain non-real ----------
    def test_http_auth_errors_stay_non_real(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        for exc in (AwinAuthError("401"), AwinPermissionError("403"),
                    AwinHTTPError("500"), AwinNetworkError("dns")):
            c = AwinLiveClient(env, transport=StubProduction(raise_exc=exc))
            with self.assertRaises(AwinError):            # lỗi minh bạch, không mint record
                c.get_offers()

    # ---------- CTO required proof #5: empty production response remains non-real ----------
    def test_empty_production_stays_non_real(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinLiveClient(env, transport=StubProduction(payload={"programmes": []}))
        res = c.get_offers()
        self.assertTrue(res["ok"])
        self.assertEqual(res["count"], 0)                 # rỗng → không offer
        self.assertEqual(res["offers"], [])               # không bịa record real nào

    # ---------- CTO required proof #6: only verified production records reach PRODUCTION_VERIFIED ----------
    def test_only_production_transport_reaches_verified(self):
        creds = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "5"}
        self.assertEqual(AwinLiveClient(creds, transport=FakeTransport())._state(), "TEST")
        self.assertEqual(AwinLiveClient({}, transport=ProductionTransport())._state(), "TEST")
        self.assertEqual(AwinLiveClient(creds, transport=ProductionTransport())._state(),
                         "PRODUCTION_VERIFIED")
        # production KHÔNG được ghi vào SQLite (phải Postgres/LIVE)
        c = AwinLiveClient(creds, transport=ProductionTransport())
        with self.assertRaises(ProductionStorageError):
            c.ingest_transactions(Repo(data_state="TEST"), "2026-09-01", "2026-09-30")

    # ---------- currency: production never assumes VND ----------
    def test_production_currency_required(self):
        creds = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "5"}
        c = AwinLiveClient(creds, transport=StubProduction(payload={"programmes": [{"id": 111}]}))
        with self.assertRaises(AwinCurrencyError):        # thiếu currency → không mặc định VND
            c.get_offers()

    def test_production_transport_flag(self):
        self.assertTrue(ProductionTransport.is_production)
        c = AwinLiveClient({"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "5"},
                           transport=ProductionTransport())
        self.assertEqual(c._state(), "PRODUCTION_VERIFIED")
        self.assertEqual(c.chain_status()["data_state"], "PRODUCTION_VERIFIED")


if __name__ == "__main__":
    unittest.main()
