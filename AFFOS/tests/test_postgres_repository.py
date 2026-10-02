"""QA — PostgresRepository minimum LIVE functionality (REAL-COMMERCE GATE #1).

Proves the enabled adapter via an INJECTED fake connection (no real DB, no driver):
  - insert() builds parameterized SQL (%s) with ON CONFLICT upsert;
  - provenance guard: only LIVE/PRODUCTION_VERIFIED accepted on prov tables;
  - query()/count() shape results correctly;
  - no-credential construction still raises (gated), no silent SQLite fallback.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
from repository import PostgresRepository, SqliteRepository, select_repository  # noqa: E402


class FakeCursor:
    def __init__(self, store):
        self.store = store
        self.description = None
        self._rows = []

    def execute(self, sql, params=()):
        self.store["last_sql"] = sql
        self.store["last_params"] = tuple(params)
        self.store.setdefault("log", []).append(sql)
        if sql.strip().upper().startswith("SELECT COUNT"):
            self._rows = [(self.store.get("count", 0),)]
            self.description = [("count",)]
        elif sql.strip().upper().startswith("SELECT"):
            self.description = [("id",), ("amount",)]
            self._rows = self.store.get("select_rows", [("CO-1", 7)])

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, store):
        self.store = store
    def cursor(self):
        return FakeCursor(self.store)
    def commit(self):
        self.store["committed"] = self.store.get("committed", 0) + 1


class TestPostgresRepository(unittest.TestCase):
    def test_requires_credentials_when_no_conn(self):
        with self.assertRaises(RuntimeError):
            PostgresRepository({})                      # no URL, no injected conn
        self.assertIsInstance(select_repository({}), SqliteRepository)

    def test_scope_rejects_non_live_state(self):
        store = {}
        with self.assertRaises(ValueError):
            PostgresRepository(conn=FakeConn(store), data_state="SEEDED")

    def test_insert_builds_upsert_sql_and_enforces_provenance(self):
        store = {}
        repo = PostgresRepository(conn=FakeConn(store), data_state="PRODUCTION_VERIFIED")
        # missing data_state on a provenance table → rejected
        with self.assertRaises(ValueError):
            repo.insert("commissions", {"id": "CO-1", "amount": 7})
        # SEEDED on a LIVE repo → rejected (no seed masquerading as production)
        with self.assertRaises(ValueError):
            repo.insert("commissions", {"id": "CO-1", "amount": 7, "data_state": "SEEDED"})
        # valid LIVE insert builds parameterized upsert
        repo.insert("commissions", {"id": "CO-1", "amount": 7, "data_state": "PRODUCTION_VERIFIED"})
        sql = store["last_sql"]
        self.assertIn("INSERT INTO commissions", sql)
        self.assertIn("%s", sql)                        # parameterized, not string-formatted values
        self.assertIn("ON CONFLICT (id) DO UPDATE SET", sql)
        self.assertEqual(store["committed"], 1)

    def test_query_and_count(self):
        store = {"count": 3, "select_rows": [("CO-1", 7), ("CO-2", 9)]}
        repo = PostgresRepository(conn=FakeConn(store), data_state="LIVE")
        rows = repo.query("SELECT id, amount FROM commissions")
        self.assertEqual(rows[0], {"id": "CO-1", "amount": 7})
        self.assertEqual(repo.count("commissions"), 3)

    def test_count_rejects_unknown_table(self):
        repo = PostgresRepository(conn=FakeConn({}), data_state="LIVE")
        with self.assertRaises(ValueError):
            repo.count("not_a_table")


if __name__ == "__main__":
    unittest.main()
