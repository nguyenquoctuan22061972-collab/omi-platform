"""QA — AWIN DRY-RUN ingestion (S5B). Offline, no network, no credentials, no production API.

Verifies the reused AWIN connector's real schema mapping + provenance, and the additive path from an
AWIN transaction to RevenueStore.write_conversion_chain() with row-level dedupe. Impact stays OFF
(not touched here). AWIN is driven with a FakeTransport — never a production transport.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))

import provenance  # noqa: E402
import revenue_store  # noqa: E402
import awin_mapping  # noqa: E402
from data_access import Repo  # noqa: E402
from awin_live import AwinLiveClient, Transport  # noqa: E402

CREDS = {"AWIN_API_TOKEN": "t", "AWIN_PUBLISHER_ID": "123"}
TXNS = [
    {"id": 1001, "advertiserId": 55, "commissionStatus": "approved",
     "saleAmount": {"amount": 200.0, "currency": "USD"},
     "commissionAmount": {"amount": 30.0, "currency": "USD"},
     "clickDate": "2026-10-05", "transactionDate": "2026-10-06"},
    {"id": 1002, "advertiserId": 55, "commissionStatus": "pending",
     "saleAmount": {"amount": 100.0, "currency": "USD"},
     "commissionAmount": {"amount": 15.0, "currency": "USD"},
     "clickDate": "2026-10-05", "transactionDate": "2026-10-06"},
]


class FakeAwinTransport(Transport):
    is_production = False
    def get(self, url, token):
        if "transactions" in url:
            return {"transactions": TXNS}
        return {}


class TestAwinConnectorDryRun(unittest.TestCase):
    """The reused AWIN engine writes via repo.insert (INSERT OR REPLACE) — verify mapping/provenance."""
    def setUp(self):
        self.repo = Repo(data_state="TEST")
        self.client = AwinLiveClient(CREDS, transport=FakeAwinTransport())

    def test_mapping_and_provenance(self):
        res = self.client.ingest_transactions(self.repo, "2026-10-01", "2026-10-07")
        self.assertEqual(res["ingested"], 2)
        self.assertEqual(res["data_state"], "TEST")
        co = self.repo.query("SELECT * FROM commissions WHERE id='CO-1001'")[0]
        self.assertEqual(co["amount"], 30.0)
        self.assertEqual(co["status"], "APPROVED")
        self.assertEqual(co["source"], "awin_fake_test")          # never a production source
        self.assertEqual(co["source_record_id"], "CO-1001")       # provenance carries the record id
        self.assertFalse(provenance.is_real(co))                  # TEST data is never real
        cv = self.repo.query("SELECT * FROM conversion_events WHERE id='CV-1001'")[0]
        self.assertEqual(cv["offer_id"], "OF-55")                 # advertiserId -> offer
        self.assertEqual(cv["order_value"], 200.0)

    def test_reingest_no_duplicate(self):
        self.client.ingest_transactions(self.repo, "2026-10-01", "2026-10-07")
        self.client.ingest_transactions(self.repo, "2026-10-01", "2026-10-07")   # replay same window
        self.assertEqual(self.repo.count("commissions"), 2)       # upsert by id -> no duplicates
        self.assertEqual(self.repo.count("conversion_events"), 2)


class TestAwinToWriteChain(unittest.TestCase):
    """Additive path: AWIN transaction -> map_awin_transaction -> write_conversion_chain (durable)."""
    def setUp(self):
        self.repo = Repo(data_state="DRY_RUN")
        self.store = revenue_store.RevenueStore(self.repo.conn, "?")
        self.store.init_schema(with_commission_unique=True)

    def test_map_fields(self):
        a = awin_mapping.map_awin_transaction(TXNS[0])
        self.assertEqual(a["source_record_id"], "1001")
        self.assertEqual(a["offer_id"], "OF-55")
        self.assertEqual(a["order_value"], 200.0)
        self.assertEqual(a["commission_amount"], 30.0)
        self.assertEqual(a["currency"], "USD")
        self.assertEqual(a["status"], "APPROVED")

    def test_durable_ingest_and_dedupe(self):
        r1 = awin_mapping.ingest_transactions_durable(self.store, TXNS)
        self.assertEqual(r1["written"], 2)
        self.assertEqual(self.repo.count("commissions"), 2)
        r2 = awin_mapping.ingest_transactions_durable(self.store, TXNS)   # replay -> idempotent skip
        self.assertEqual(r2["skipped"], 2)
        self.assertEqual(self.repo.count("commissions"), 2)               # still no duplicate

    def test_duplicate_raises_when_not_skipping(self):
        a = awin_mapping.map_awin_transaction(TXNS[0])
        self.assertTrue(self.store.write_conversion_chain(a))
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.write_conversion_chain(a, on_duplicate="raise")
        self.assertEqual(self.repo.count("commissions"), 1)

    def test_malformed_transaction_is_counted_not_written(self):
        bad = [{"advertiserId": 9, "commissionStatus": "approved"}]   # missing id
        r = awin_mapping.ingest_transactions_durable(self.store, bad)
        self.assertEqual(r["errors"], 1)
        self.assertEqual(r["written"], 0)
        self.assertEqual(self.repo.count("commissions"), 0)


if __name__ == "__main__":
    unittest.main()
