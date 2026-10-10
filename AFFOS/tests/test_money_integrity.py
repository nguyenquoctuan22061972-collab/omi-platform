"""QA — MONEY P0 correctness fixes (status, refunds, zero-revenue, currency, proof scope,
attribution linkage, idempotency). All offline; no credentials, no live call."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "core", "attribution"))
sys.path.insert(0, os.path.join(ROOT, "core", "economics"))

import economics            # noqa: E402
import provenance           # noqa: E402
import money_status         # noqa: E402
import attribution          # noqa: E402
import proof                # noqa: E402
from data_access import Repo  # noqa: E402


def _prov(source, rid, ds, cur, verified=False):
    return provenance.provenance(source, rid, ds, currency=cur, is_verified=verified)


def _seed_commission(repo, cid, amount, status, currency="USD", ds="SEEDED", source="seed", verified=False):
    cv = "CV-" + cid
    repo.insert("conversion_events", {"id": cv, "click_event_id": "", "offer_id": "OF-1",
                "order_value": amount, "status": status, "ts": "t", "event_subtype": "SEEDED_CONVERSION",
                **_prov(source, cv, ds, currency, verified)})
    repo.insert("commissions", {"id": "CO-" + cid, "conversion_event_id": cv,
                "amount": amount, "status": status, **_prov(source, "CO-" + cid, ds, currency, verified)})


class TestStatusCanonical(unittest.TestCase):
    def test_canonical_sets(self):
        self.assertTrue(money_status.is_confirmed("approved"))
        self.assertTrue(money_status.is_confirmed("CONFIRMED"))
        self.assertTrue(money_status.is_refund("REFUNDED"))
        self.assertTrue(money_status.is_refund("reversed"))
        for s in ("PENDING", "DECLINED", "CANCELLED"):
            self.assertFalse(money_status.is_confirmed(s))
            self.assertFalse(money_status.is_refund(s))

    def test_only_confirmed_counts_as_revenue(self):
        repo = Repo(data_state="SEEDED")
        _seed_commission(repo, "A", 100, "APPROVED")      # counts
        _seed_commission(repo, "B", 50, "PENDING")        # NOT counted
        _seed_commission(repo, "C", 40, "DECLINED")       # NOT counted
        t = attribution.totals(repo)
        self.assertEqual(t["gross_revenue"], 100.0)       # only APPROVED
        self.assertEqual(t["revenue"], 100.0)


class TestRefundSemantics(unittest.TestCase):
    def test_refund_subtracted_once(self):
        repo = Repo(data_state="SEEDED")
        _seed_commission(repo, "A", 100, "APPROVED")
        _seed_commission(repo, "B", 30, "REFUNDED")
        t = attribution.totals(repo)
        self.assertEqual(t["gross_revenue"], 100.0)
        self.assertEqual(t["refunds"], 30.0)
        self.assertEqual(t["revenue"], 70.0)              # 100 − 30, exactly once
        self.assertEqual(t["contribution_profit"], 70.0)  # no costs → equals net


class TestZeroRevenueHealth(unittest.TestCase):
    def test_zero_revenue_not_healthy(self):
        r = economics.ai_revenue_ratio(10, 0)
        self.assertFalse(r["healthy"])
        self.assertEqual(r["status"], "NO_REVENUE_DATA")
        self.assertIsNone(r["ratio_pct"])

    def test_positive_revenue_ok(self):
        r = economics.ai_revenue_ratio(5.2, 31)
        self.assertEqual(r["status"], "OK")
        self.assertTrue(r["healthy"])


class TestCurrencyAggregation(unittest.TestCase):
    def test_mixed_currency_refuses_single_number(self):
        repo = Repo(data_state="SEEDED")
        _seed_commission(repo, "U", 100, "APPROVED", currency="USD")
        _seed_commission(repo, "V", 2000, "APPROVED", currency="VND")
        t = attribution.totals(repo)
        self.assertTrue(t["mixed_currency"])
        self.assertIsNone(t["revenue"])                   # never collapse USD+VND
        self.assertEqual(set(t["currencies"]), {"USD", "VND"})
        self.assertEqual(t["by_currency"]["USD"]["revenue"], 100.0)

    def test_currency_filter_single(self):
        repo = Repo(data_state="SEEDED")
        _seed_commission(repo, "U", 100, "APPROVED", currency="USD")
        _seed_commission(repo, "V", 2000, "APPROVED", currency="VND")
        t = attribution.totals(repo, currency="USD")
        self.assertFalse(t["mixed_currency"])
        self.assertEqual(t["revenue"], 100.0)
        self.assertEqual(t["currency"], "USD")


class TestRevenueLabel(unittest.TestCase):
    def test_label_reflects_verification(self):
        self.assertEqual(provenance.revenue_label("PRODUCTION_VERIFIED"), "PRODUCTION_REVENUE")
        self.assertEqual(provenance.revenue_label("LIVE"), "UNVERIFIED_REVENUE")  # LIVE ≠ REAL
        self.assertEqual(provenance.revenue_label("SEEDED"), "SIMULATED_REVENUE")


class TestProofScopeAndLinkage(unittest.TestCase):
    def test_unrelated_data_does_not_falsify_scope(self):
        repo = Repo(data_state="SEEDED")
        _seed_commission(repo, "OLD", 100, "APPROVED")    # unrelated, unlinked
        pr = proof.real_commerce_proof(repo, campaign_id="C-EXP-001")
        self.assertEqual(pr["status"], "NOT YET VERIFIED")
        self.assertEqual(pr["scope"], "C-EXP-001")

    def test_attribution_linkage_flag(self):
        repo = Repo(data_state="SEEDED")
        _seed_commission(repo, "A", 100, "APPROVED")      # click_event_id empty → unlinked
        pr = proof.real_commerce_proof(repo)
        self.assertFalse(pr["attribution_linked"])
        self.assertTrue(any("attribution" in r for r in pr["reasons"]))


class TestIdempotentIngest(unittest.TestCase):
    def test_reinsert_same_id_no_duplicate(self):
        repo = Repo(data_state="SEEDED")
        for _ in range(3):                                 # repeated ingest of same source id
            _seed_commission(repo, "DUP", 100, "APPROVED")
        self.assertEqual(repo.count("commissions"), 1)     # upsert by id, not duplicated
        self.assertEqual(attribution.totals(repo)["revenue"], 100.0)


if __name__ == "__main__":
    unittest.main()
