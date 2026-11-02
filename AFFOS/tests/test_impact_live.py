"""QA — Impact adapter (AFFOS.1). DRY-RUN + economic-truth proofs. No credentials needed.

Mirrors the AWIN live proofs and adds the AFFOS.1-specific guarantee: Impact records are
NEVER is_real() yet (impact_production not in PRODUCTION_SOURCES). AWIN is not imported/affected.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "impact"))

import provenance, proof                 # noqa: E402
from data_access import Repo             # noqa: E402
from impact_live import (                # noqa: E402
    ImpactLiveClient, Transport, ProductionTransport,
    ImpactError, ImpactAuthError, ImpactPermissionError, ImpactHTTPError,
    ImpactNetworkError, ImpactCurrencyError, ProductionStorageError,
)
from adapters import ImpactAdapter, get_connector   # noqa: E402
from connector_interface import verify_contract     # noqa: E402


class FakeTransport(Transport):
    is_production = False
    def get(self, url, auth_header):
        if "/Items" in url:                        # catalog items (under a catalog)
            return {"Items": [{"CatalogItemId": 501, "Name": "Widget", "CurrentPrice": 9.99,
                               "PayoutRate": 0.30, "Currency": "USD"}]}
        if "/Catalogs" in url:                      # catalog list (one per advertiser)
            return {"Catalogs": [{"Id": 77, "AdvertiserId": 501, "AdvertiserName": "Acme"}]}
        if "Actions" in url:
            return {"Actions": [{"Id": 9001, "CampaignId": 501, "Amount": 200,
                    "Payout": 60, "Currency": "USD", "State": "APPROVED",
                    "ClickDate": "2026-10-05", "EventDate": "2026-10-06"}]}
        return {}


class StubProduction(ProductionTransport):
    def __init__(self, raise_exc=None, payload=None):
        self.raise_exc = raise_exc
        self.payload = {} if payload is None else payload
    def get(self, url, auth_header):
        if not auth_header:
            raise ImpactAuthError("missing credentials")
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.payload


CREDS = {"IMPACT_ACCOUNT_SID": "SID123", "IMPACT_AUTH_TOKEN": "tok"}


class TestImpactLive(unittest.TestCase):
    def test_blocked_without_credentials(self):
        c = ImpactLiveClient({})
        self.assertFalse(c.auth()["ok"])
        self.assertIn("IMPACT_ACCOUNT_SID", c.auth()["blocked"])

    def test_adapter_contract(self):
        a = ImpactAdapter({})
        chk = verify_contract(a)
        self.assertTrue(chk["contract_ok"], chk)
        self.assertEqual(a.mode(), "DRY-RUN")
        self.assertIs(get_connector("impact").__class__, ImpactAdapter)

    def test_fake_transport_wiring_but_not_real(self):
        c = ImpactLiveClient(CREDS, transport=FakeTransport())
        self.assertTrue(c.auth()["ok"])
        offers = c.get_offers()
        self.assertTrue(offers["ok"])
        self.assertEqual(offers["offers"][0]["data_state"], "TEST")
        repo = Repo(data_state="TEST")
        ing = c.ingest_actions(repo, "2026-10-01", "2026-10-06")
        self.assertEqual(ing["ingested"], 1)
        self.assertEqual(ing["data_state"], "TEST")
        self.assertEqual(proof.real_commerce_proof(repo)["status"], "NOT YET VERIFIED")
        self.assertFalse(provenance.is_real(repo.query("SELECT * FROM commissions")[0]))

    def test_impact_production_real_when_verified(self):
        # CTO-approved whitelist: impact_production IS in PRODUCTION_SOURCES now, so a
        # production-transport + verified record is_real()==True. Fake/TEST stays non-real.
        c = ImpactLiveClient(CREDS, transport=ProductionTransport())
        self.assertEqual(c._state(), "PRODUCTION_VERIFIED")
        rec = c._prov("X-1", currency="USD")
        self.assertTrue(provenance.is_real(rec))        # whitelisted production source
        # fake/test transport must still never be real
        f = ImpactLiveClient(CREDS, transport=FakeTransport())
        self.assertFalse(provenance.is_real(f._prov("X-2", currency="USD")))

    def test_production_requires_credentials(self):
        c = ImpactLiveClient({"IMPACT_ACCOUNT_SID": "SID"}, transport=ProductionTransport())
        self.assertFalse(c.auth()["ok"])
        with self.assertRaises(ImpactAuthError):
            ProductionTransport().get("https://api.impact.com/x", "")

    def test_errors_stay_non_real(self):
        for exc in (ImpactAuthError("401"), ImpactPermissionError("403"),
                    ImpactHTTPError("500"), ImpactNetworkError("dns")):
            c = ImpactLiveClient(CREDS, transport=StubProduction(raise_exc=exc))
            with self.assertRaises(ImpactError):
                c.get_offers()

    def test_empty_production_stays_non_real(self):
        c = ImpactLiveClient(CREDS, transport=StubProduction(payload={"Catalogs": []}))
        r = c.get_offers()
        self.assertTrue(r["ok"])
        self.assertEqual(r["count"], 0)

    def test_production_currency_required(self):
        # catalog present + item without Currency → production record must raise (no VND default)
        c = ImpactLiveClient(CREDS, transport=StubProduction(payload={
            "Catalogs": [{"Id": 1, "AdvertiserId": 2}], "Items": [{"CatalogItemId": 9}]}))
        with self.assertRaises(ImpactCurrencyError):
            c.get_offers()

    def test_production_write_to_sqlite_refused(self):
        c = ImpactLiveClient(CREDS, transport=ProductionTransport())
        with self.assertRaises(ProductionStorageError):
            c.ingest_actions(Repo(data_state="TEST"), "2026-10-01", "2026-10-06")

    def test_chain_status_blocked(self):
        st = ImpactLiveClient({}).chain_status()
        self.assertFalse(st["ready_for_real"])
        self.assertEqual(st["provider"], "impact")
        self.assertEqual(len(st["steps"]), 9)


class _MemLiveRepo:
    """Non-SQLite LIVE repo double so the production write-guard passes (no real DB)."""
    data_state = "LIVE"
    def __init__(self): self.rows = {}
    def insert(self, table, row): self.rows.setdefault(table, []).append(row)
    def query(self, sql, params=()): return []
    def count(self, table): return len(self.rows.get(table, []))


class _CapturingProd(ProductionTransport):
    """Production-flagged transport that records request URLs (no network)."""
    def __init__(self, payload):
        self.payload = payload
        self.urls = []
    def get(self, url, auth_header):
        self.urls.append(url)
        if not auth_header:
            raise ImpactAuthError("missing credentials")
        return self.payload


class TestImpactActionsRequest(unittest.TestCase):
    ACTION = {"Id": 1, "CampaignId": 9, "Amount": 100, "Payout": 30,
              "Currency": "USD", "State": "APPROVED",
              "ClickDate": "2026-10-05", "EventDate": "2026-10-06"}

    def test_ingest_actions_uses_impact_date_params(self):
        t = _CapturingProd({"Actions": [self.ACTION]})
        c = ImpactLiveClient(CREDS, transport=t)
        res = c.ingest_actions(_MemLiveRepo(), "2026-10-01", "2026-10-06")
        self.assertEqual(res["ingested"], 1)
        url = t.urls[-1]
        self.assertIn("/Mediapartners/SID123/Actions", url)
        self.assertIn("ActionDateStart=2026-10-01", url)   # Impact contract param
        self.assertIn("ActionDateEnd=2026-10-06", url)
        self.assertNotIn("StartDate=", url)                 # old wrong param gone
        self.assertNotIn("EndDate=", url)

    def test_adapter_actions_reads_use_impact_date_params(self):
        t = _CapturingProd({"Actions": []})
        a = ImpactAdapter(CREDS, transport=t)
        a.get_conversions("2026-10-01", "2026-10-06")
        url = t.urls[-1]
        self.assertIn("/Mediapartners/SID123/Actions", url)
        self.assertIn("ActionDateStart=2026-10-01", url)
        self.assertIn("ActionDateEnd=2026-10-06", url)
        self.assertNotIn("StartDate=", url)

    def test_production_auth_header_is_basic(self):
        # request carries HTTP Basic auth (Impact contract); creds never logged by the client.
        c = ImpactLiveClient(CREDS, transport=_CapturingProd({"Items": []}))
        self.assertTrue(c._auth_header().startswith("Basic "))


class TestImpactDatetimeAndErrors(unittest.TestCase):
    """HOTFIX 2: ISO-8601 date-time params (root cause of HTTP 400) + 400-body diagnostics."""

    def test_iso8601_helper(self):
        from impact_live import iso8601
        self.assertEqual(iso8601("2026-10-01"), "2026-10-01T00:00:00Z")   # bare date → date-time
        self.assertEqual(iso8601("2026-10-01T06:30:00Z"), "2026-10-01T06:30:00Z")  # passthrough
        self.assertEqual(iso8601(""), "")

    def test_bare_date_sent_as_iso_datetime(self):
        t = _CapturingProd({"Actions": []})
        ImpactAdapter(CREDS, transport=t).get_conversions("2026-10-01", "2026-10-06")
        url = t.urls[-1]
        # ':' is percent-encoded; bare date expanded to midnight UTC
        self.assertIn("ActionDateStart=2026-10-01T00%3A00%3A00Z", url)
        self.assertIn("ActionDateEnd=2026-10-06T00%3A00%3A00Z", url)
        self.assertIn("Page=1", url)
        self.assertIn("PageSize=100", url)

    def test_datetime_passthrough(self):
        t = _CapturingProd({"Actions": []})
        c = ImpactLiveClient(CREDS, transport=t)
        c.ingest_actions(_MemLiveRepo(), "2026-10-01T06:30:00Z", "2026-10-06T23:59:59Z")
        url = t.urls[-1]
        self.assertIn("ActionDateStart=2026-10-01T06%3A30%3A00Z", url)
        self.assertNotIn("T00%3A00%3A00ZT", url)   # no double time component

    def test_offer_discovery_uses_catalogs_then_items(self):
        t = _CapturingProd({})          # payload set per-url below via subclass
        class _CatProd(ProductionTransport):
            def __init__(s): s.urls = []
            def get(s, url, auth_header):
                s.urls.append(url)
                if "/Items" in url:
                    return {"Items": [{"CatalogItemId": 501, "Name": "Widget",
                                       "CurrentPrice": 9.99, "PayoutRate": 0.3, "Currency": "USD"}]}
                if "/Catalogs" in url:
                    return {"Catalogs": [{"Id": 77, "AdvertiserId": 501, "AdvertiserName": "Acme"}]}
                return {}
        cp = _CatProd()
        c = ImpactLiveClient(CREDS, transport=cp)
        res = c.get_offers()
        self.assertTrue(res["ok"])
        self.assertEqual(res["count"], 1)
        o = res["offers"][0]
        self.assertEqual(o["product_id"], "501")
        self.assertEqual(o["catalog_id"], "77")
        self.assertEqual(o["merchant_id"], "M-501")
        # endpoint contract: a /Catalogs list call AND a /Catalogs/{id}/Items call were issued
        self.assertTrue(any(u.endswith("/Catalogs?Page=1&PageSize=100") for u in cp.urls))
        self.assertTrue(any("/Catalogs/77/Items" in u for u in cp.urls))
        self.assertFalse(any("/Catalogs/Items" in u for u in cp.urls))   # old wrong endpoint gone

    def test_adapter_merchant_product_mapping(self):
        a = ImpactAdapter(CREDS, transport=FakeTransport())
        self.assertEqual(a.mode(), "DRY-RUN")       # fake transport → never LIVE
        m = a.get_merchants()["items"]
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["id"], "M-501")
        self.assertEqual(m[0]["name"], "Acme")
        p = a.get_products()["items"]
        self.assertEqual(p[0]["id"], "501")
        self.assertEqual(p[0]["merchant_id"], "M-501")
        self.assertEqual(p[0]["catalog_id"], "77")

    def test_http_400_body_is_surfaced(self):
        import io
        import urllib.error
        from unittest import mock
        err = urllib.error.HTTPError("https://api.impact.com/x", 400, "Bad Request", {},
                                     io.BytesIO(b"Invalid ActionDateStart format"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ImpactHTTPError) as cm:
                ProductionTransport().get("https://api.impact.com/x", "Basic xxx")
        msg = str(cm.exception)
        self.assertIn("400", msg)
        self.assertIn("Invalid ActionDateStart", msg)   # body no longer hidden


if __name__ == "__main__":
    unittest.main()
