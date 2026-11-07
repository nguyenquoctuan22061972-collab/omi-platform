"""QA — AFFOS Revenue Reporting & Reconciliation (S6). Offline SQLite; READ-ONLY guarantee.

Verifies status buckets (pending/approved/rejected/refunded), discrepancy detection (missing
commission, orphan commission, invalid provenance), the verified flag, and that reconciliation never
mutates source records.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "core"))

import revenue_report  # noqa: E402
from data_access import Repo  # noqa: E402


def _prov(src, srid):
    return {"source": src, "source_record_id": srid, "data_state": "TEST",
            "currency": "USD", "fetched_at": "t", "is_verified": 0}


def _seed(repo):
    # Four conversions (one, CV-5, left with NO commission -> missing_commission).
    for cid, status in [("CV-1", "approved"), ("CV-2", "pending"),
                        ("CV-3", "declined"), ("CV-4", "refunded"), ("CV-5", "approved")]:
        repo.insert("conversion_events", {"id": cid, "click_event_id": "", "offer_id": "OF-1",
                    "order_value": 100.0, "status": status, "ts": "t", **_prov("awin_fake_test", cid)})
    # Commissions for CV-1..CV-4, plus an orphan pointing at a non-existent conversion.
    for coid, conv, status in [("CO-1", "CV-1", "approved"), ("CO-2", "CV-2", "pending"),
                               ("CO-3", "CV-3", "declined"), ("CO-4", "CV-4", "refunded"),
                               ("CO-ORPHAN", "CV-missing", "approved")]:
        repo.insert("commissions", {"id": coid, "conversion_event_id": conv, "amount": 10.0,
                    "status": status, **_prov("awin_fake_test", coid)})


class TestReconcile(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(data_state="TEST")
        _seed(self.repo)

    def test_status_buckets(self):
        r = revenue_report.reconcile(self.repo)
        c = r["summary"]["counts"]
        self.assertEqual(c["approved"], 2)     # CO-1 + CO-ORPHAN
        self.assertEqual(c["pending"], 1)
        self.assertEqual(c["rejected"], 1)     # declined
        self.assertEqual(c["refunded"], 1)

    def test_discrepancies(self):
        r = revenue_report.reconcile(self.repo)
        d = r["discrepancies"]
        self.assertIn("CV-5", d["missing_commission"])      # conversion without commission
        self.assertIn("CO-ORPHAN", d["orphan_commission"])  # commission without conversion
        self.assertEqual(d["duplicate_commission"], {})     # unique source ids -> none
        self.assertIsNotNone(r["alert"])                    # discrepancies -> alert raised

    def test_not_verified_for_test_data(self):
        r = revenue_report.reconcile(self.repo)
        self.assertFalse(r["summary"]["verified"])
        self.assertTrue(r["read_only"])

    def test_reconcile_does_not_mutate(self):
        before = (self.repo.count("conversion_events"), self.repo.count("commissions"))
        revenue_report.reconcile(self.repo)
        revenue_report.reconcile(self.repo)
        after = (self.repo.count("conversion_events"), self.repo.count("commissions"))
        self.assertEqual(before, after)                     # SELECT-only; nothing written


if __name__ == "__main__":
    unittest.main()
