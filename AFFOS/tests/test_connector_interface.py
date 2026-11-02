"""QA — Connector Interface (FAST-TRACK #03 Phase 2).

Proves: both adapters satisfy the 8-capability contract; modes are honest
(SEED/DRY-RUN/LIVE, never REAL self-declared); AWIN blocked without creds;
fake transport stays non-production; factory rejects unregistered networks.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))

from connector_interface import Connector, CAPABILITIES, MODES, verify_contract  # noqa: E402
from adapters import (AffiliateNetworkAdapter, AwinAdapter, get_connector)       # noqa: E402
from awin_live import ProductionTransport, Transport                             # noqa: E402


class FakeTransport(Transport):
    is_production = False
    def get(self, url, token):
        if "programmes" in url:
            return {"programmes": [{"id": 111, "commissionRate": 0.07, "currencyCode": "USD"}]}
        if "transactions" in url:
            return {"transactions": [{"id": 900, "saleAmount": {"amount": 100, "currency": "USD"},
                    "commissionAmount": {"amount": 7, "currency": "USD"},
                    "commissionStatus": "confirmed", "clickDate": "2026-09-29"}]}
        return {}


class TestConnectorContract(unittest.TestCase):
    def test_exactly_eight_capabilities(self):
        self.assertEqual(len(CAPABILITIES), 8)
        self.assertEqual(set(CAPABILITIES), {
            "get_merchants", "get_products", "get_offers", "get_commission",
            "create_tracking_link", "get_clicks", "get_conversions", "get_revenue"})
        self.assertNotIn("REAL", MODES)   # REAL never self-declared by a connector

    def test_affiliate_network_adapter_contract(self):
        c = AffiliateNetworkAdapter({})
        self.assertIsInstance(c, Connector)
        chk = verify_contract(c)
        self.assertTrue(chk["contract_ok"], chk)
        self.assertEqual(chk["missing_capabilities"], [])
        self.assertEqual(c.mode(), "SEED")               # dry-run serves seed catalog
        self.assertTrue(c.get_offers()["items"])
        self.assertTrue(c.get_products()["items"])
        self.assertTrue(c.get_commission()["items"])
        # seed connector has no real clicks/conversions/revenue
        self.assertEqual(c.get_clicks()["items"], [])
        self.assertEqual(c.get_conversions()["items"], [])

    def test_awin_adapter_contract_and_blocked_without_creds(self):
        c = AwinAdapter({})
        self.assertIsInstance(c, Connector)
        chk = verify_contract(c)
        self.assertTrue(chk["contract_ok"], chk)
        self.assertEqual(c.mode(), "DRY-RUN")            # no creds/transport → not LIVE
        for cap in ("get_offers", "get_merchants", "get_products",
                    "get_commission", "get_clicks", "get_conversions", "get_revenue"):
            r = getattr(c, cap)()
            self.assertFalse(r["ok"], cap)               # blocked without creds
            self.assertEqual(r["items"], [], cap)

    def test_awin_fake_transport_is_dry_run_not_live(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinAdapter(env, transport=FakeTransport())
        self.assertEqual(c.mode(), "DRY-RUN")            # fake transport → never LIVE
        offers = c.get_offers()
        self.assertTrue(offers["ok"])
        self.assertEqual(offers["mode"], "DRY-RUN")      # items labeled non-live
        convs = c.get_conversions("2026-09-01", "2026-09-30")
        self.assertEqual(convs["mode"], "DRY-RUN")
        self.assertTrue(convs["items"])                  # wiring works, but NOT live/real

    def test_awin_mode_live_only_with_production_transport(self):
        env = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "555"}
        c = AwinAdapter(env, transport=ProductionTransport())
        self.assertEqual(c.mode(), "LIVE")               # production transport + creds
        # deep link is buildable without a network call
        dl = c.create_tracking_link("111", "https://shop.example/p", "ref1")
        self.assertIn("awin1.com/cread.php", dl["items"][0]["url"])

    def test_factory_rejects_unregistered(self):
        self.assertIsInstance(get_connector("awin"), AwinAdapter)
        self.assertIsInstance(get_connector("affiliate_network"), AffiliateNetworkAdapter)
        # impact is now registered (AFFOS.1); the rest remain unregistered.
        for not_yet in ("impact.com", "amazon", "shopee", "tiktok", "youtube"):
            with self.assertRaises(ValueError):
                get_connector(not_yet)


if __name__ == "__main__":
    unittest.main()
