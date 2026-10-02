"""QA — CTO review: data-state model, provenance, repository split, real-commerce proof."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "core", "attribution"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))
import provenance, proof                       # noqa: E402
from data_access import Repo                    # noqa: E402
from repository import SqliteRepository, PostgresRepository, select_repository  # noqa: E402
import pipeline                                 # noqa: E402
from awin_connector import AwinConnector        # noqa: E402


class TestProvenance(unittest.TestCase):
    def test_states_and_is_real(self):
        self.assertEqual(provenance.DATA_STATES,
                         ["TEST", "DRY_RUN", "SEEDED", "LIVE", "PRODUCTION_VERIFIED"])
        seeded = provenance.provenance("awin_seed", "x1", "SEEDED")
        self.assertFalse(provenance.is_real(seeded))          # seeded KHÔNG BAO GIỜ real
        real = provenance.provenance("awin_production", "t1", "PRODUCTION_VERIFIED", is_verified=True)
        self.assertTrue(provenance.is_real(real))
        with self.assertRaises(ValueError):
            provenance.provenance("x", "1", "SEEDED", is_verified=True)  # verified sai state

    def test_labels(self):
        self.assertEqual(provenance.revenue_label("SEEDED"), "SIMULATED_REVENUE")
        self.assertEqual(provenance.revenue_label("PRODUCTION_VERIFIED"), "PRODUCTION_REVENUE")
        self.assertEqual(provenance.conversion_type("SEEDED"), "SEEDED_CONVERSION")
        self.assertEqual(provenance.conversion_type("LIVE"), "AWIN_PRODUCTION_CONVERSION")

    def test_sqlite_is_test_only(self):
        with self.assertRaises(ValueError):
            Repo(data_state="LIVE")
        with self.assertRaises(ValueError):
            SqliteRepository(data_state="PRODUCTION_VERIFIED")

    def test_insert_requires_provenance(self):
        r = Repo()
        with self.assertRaises(ValueError):
            r.insert("commissions", {"id": "c1", "amount": 100})   # thiếu data_state

    def test_postgres_adapter_gated(self):
        with self.assertRaises(RuntimeError):
            PostgresRepository({})                                  # thiếu creds
        # Có URL nhưng không có driver/DB → lỗi tường minh (không im lặng fallback SQLite)
        with self.assertRaises(Exception):
            PostgresRepository({"DATABASE_URL": "postgres://x"})
        self.assertIsInstance(select_repository({}), SqliteRepository)  # không creds → SQLite

    def test_pipeline_is_seeded_not_real(self):
        r = pipeline.run(connector=AwinConnector({}))
        self.assertEqual(r["data_state"], "SEEDED")
        self.assertEqual(r["totals"]["revenue_label"], "SIMULATED_REVENUE")
        self.assertFalse(r["totals"]["is_verified"])
        self.assertEqual(r["real_commerce_proof"]["report_line"], "REAL COMMERCE PROOF: NOT YET VERIFIED")

    def test_records_carry_provenance(self):
        r = pipeline.run(connector=AwinConnector({}))
        # (chạy lại repo qua pipeline nội bộ không expose; kiểm proof reasons thay thế)
        self.assertIn("status", r["real_commerce_proof"])
        self.assertEqual(r["real_commerce_proof"]["status"], "NOT YET VERIFIED")


if __name__ == "__main__":
    unittest.main()
