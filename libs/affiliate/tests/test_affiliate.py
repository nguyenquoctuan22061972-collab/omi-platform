"""QA — Affiliate Registry (PRD-010 B)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.affiliate import AffiliateRegistry, NETWORKS, build_utm, deep_link  # noqa: E402


class TestAffiliate(unittest.TestCase):
    def test_five_networks(self):
        self.assertEqual(set(NETWORKS),
                         {"accesstrade", "shopee", "amazon", "tiktok_shop", "custom_partner"})

    def test_utm_builder(self):
        url = build_utm("https://x.com/p?a=1", source="shopee", campaign="t10")
        self.assertIn("utm_source=shopee", url)
        self.assertIn("utm_campaign=t10", url)
        self.assertIn("a=1", url)

    def test_tracking_from_env(self):
        r = AffiliateRegistry(env={"SHOPEE_TRACKING_ID": "tid123"})
        self.assertTrue(r.is_configured("shopee"))
        self.assertFalse(r.is_configured("amazon"))

    def test_campaign_link(self):
        r = AffiliateRegistry(env={"AMAZON_TRACKING_ID": "az"})
        link = r.campaign_link("amazon", "https://amazon.com/dp/1", campaign="c1")
        self.assertTrue(link["ready"])
        self.assertEqual(link["tracking_id"], "az")
        self.assertIn("utm_source=amazon", link["utm_url"])

    def test_deep_link_not_ready_without_tid(self):
        self.assertFalse(deep_link("shopee", "https://x", "")["ready"])

    def test_invalid_network(self):
        with self.assertRaises(KeyError):
            AffiliateRegistry().tracking_id("lazada")


if __name__ == "__main__":
    unittest.main()
