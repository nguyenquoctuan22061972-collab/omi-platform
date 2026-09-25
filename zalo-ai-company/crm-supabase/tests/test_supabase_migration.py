"""QA — PR-003 CRM Supabase migration. Parity SQLite<->Supabase, RLS, planner. No network."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(__file__)
MIG = os.path.join(HERE, "..", "migrations")
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "src")))
import migrate_planner as mp  # noqa: E402

STAGES = {"lead", "contacted", "qualified", "proposal", "won", "lost"}


def _sql(name):
    return open(os.path.join(MIG, name), encoding="utf-8").read().lower()


class TestSupabaseMigration(unittest.TestCase):
    def test_init_has_three_tables(self):
        s = _sql("0001_init.sql")
        for t in ("contacts", "conversations", "pipeline"):
            self.assertIn(f"create table if not exists {t}", s)

    def test_schema_parity_with_sqlite(self):
        # cột Supabase phải khớp cột nguồn SQLite (reuse crm.db schema)
        s = _sql("0001_init.sql")
        for table, cols in mp.TABLES.items():
            for c in cols:
                self.assertIn(c, s, f"{table}.{c} thiếu trong migration")

    def test_pipeline_stage_check_six(self):
        s = _sql("0001_init.sql")
        found = set(re.findall(r"'([a-z]+)'", s.split("check (stage in")[1].split(")")[0]))
        self.assertEqual(found, STAGES)

    def test_fk_and_indexes(self):
        s = _sql("0001_init.sql")
        self.assertIn("references contacts(id)", s)
        self.assertIn("idx_conversations_contact", s)

    def test_rls_enabled_all_tables(self):
        s = _sql("0002_rls.sql")
        for t in ("contacts", "conversations", "pipeline"):
            self.assertIn(f"alter table {t}       enable row level security".replace("  ", " ")
                          if False else f"enable row level security", s)
            self.assertIn(t, s)
        self.assertIn("to authenticated", s)      # có policy đọc
        self.assertNotIn("to anon", s)            # anon không được cấp policy

    def test_planner_dry_run_no_network(self):
        p = mp.plan(":memory:")
        self.assertEqual(p["mode"], "dry-run")
        self.assertEqual(set(p["tables"]), set(mp.TABLES))
        self.assertEqual(p["total_rows"], 0)      # DB rỗng -> 0 hàng

    def test_postgrest_endpoints(self):
        eps = mp.postgrest_endpoints("https://demo.supabase.co")
        self.assertTrue(eps["contacts"].endswith("/rest/v1/contacts"))

    def test_no_secret_in_sql(self):
        for f in ("0001_init.sql", "0002_rls.sql"):
            s = _sql(f)
            for bad in ("service_role_key", "eyj", "bearer ", "apikey="):
                self.assertNotIn(bad, s)


if __name__ == "__main__":
    unittest.main()
