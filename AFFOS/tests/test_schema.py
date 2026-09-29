"""QA — AFFOS core schema (PRD-017). 21 tables, FK, indexes, RLS, parity manifest. No network."""
import json
import os
import re
import unittest

S = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core", "schema"))


def _sql(n):
    return open(os.path.join(S, n), encoding="utf-8").read().lower()


class TestAFFOSSchema(unittest.TestCase):
    def setUp(self):
        self.man = json.load(open(os.path.join(S, "schema.manifest.json")))

    def test_manifest_21(self):
        self.assertEqual(self.man["count"], 21)
        self.assertEqual(len(self.man["tables"]), 21)

    def test_all_tables_created(self):
        s = _sql("0001_affos_core.sql")
        for t in self.man["tables"]:
            self.assertIn(f"create table if not exists {t}", s, f"thiếu bảng {t}")

    def test_has_foreign_keys(self):
        s = _sql("0001_affos_core.sql")
        for fk in ("references affiliate_networks(id)", "references merchants(id)",
                   "references products(id)", "references tracking_links(id)",
                   "references conversion_events(id)"):
            self.assertIn(fk, s)

    def test_indexes(self):
        s = _sql("0001_affos_core.sql")
        self.assertIn("idx_click_link", s)
        self.assertIn("idx_comm_conv", s)

    def test_rls_all_tables(self):
        s = _sql("0002_rls.sql")
        for t in self.man["tables"]:
            self.assertIn(f"alter table {t} enable row level security", s)
        self.assertIn("to authenticated", s)
        self.assertNotIn("to anon", s)

    def test_no_secret(self):
        for f in ("0001_affos_core.sql", "0002_rls.sql"):
            s = _sql(f)
            for bad in ("eyj", "service_role_key", "bearer ", "apikey="):
                self.assertNotIn(bad, s)


if __name__ == "__main__":
    unittest.main()
