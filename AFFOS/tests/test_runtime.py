"""QA — AFFOS production runtime wiring (SPRINT 01). No prod credentials needed."""
import json
import os
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))

import runtime                     # noqa: E402
import server                      # noqa: E402
import awin_ingest                 # noqa: E402
from repository import SqliteRepository  # noqa: E402
from awin_live import ProductionTransport, Transport  # noqa: E402


class TestRuntime(unittest.TestCase):
    def test_repository_mode_dry_run_default(self):
        self.assertEqual(runtime.repository_mode({}), "DRY-RUN")

    def test_repository_mode_live_when_db_url(self):
        self.assertEqual(runtime.repository_mode({"DATABASE_URL": "postgresql://x"}), "LIVE")
        self.assertEqual(runtime.repository_mode({"SUPABASE_DB_URL": "postgresql://y"}), "LIVE")

    def test_build_repository_dry_run_is_sqlite(self):
        repo = runtime.build_repository({})
        self.assertIsInstance(repo, SqliteRepository)
        self.assertIn(repo.data_state, ("DRY_RUN", "TEST", "SEEDED"))

    def test_health_is_secret_free_and_reports_mode(self):
        h = runtime.health({"DATABASE_URL": "postgresql://user:pass@host/db"})
        blob = json.dumps(h)
        self.assertNotIn("pass", blob)             # no secret value leaks
        self.assertNotIn("host/db", blob)
        self.assertEqual(h["repository_mode"], "LIVE")
        self.assertFalse(h["awin_live_enabled"])
        self.assertEqual(h["status"], "ok")

    def test_health_dry_run_default(self):
        self.assertEqual(runtime.health({})["repository_mode"], "DRY-RUN")

    def test_server_health_response(self):
        code, body = server.build_health_response({})
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data["repository_mode"], "DRY-RUN")
        self.assertEqual(data["service"], "affos-runtime")


class TestAwinIngestGate(unittest.TestCase):
    def test_stops_without_approval(self):
        r = awin_ingest.run_ingestion({"DATABASE_URL": "postgresql://x"}, approved=False,
                                      transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")

    def test_stops_when_dry_run(self):
        r = awin_ingest.run_ingestion({}, approved=True, transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["reason"])

    def test_stops_without_production_transport(self):
        r = awin_ingest.run_ingestion({"DATABASE_URL": "postgresql://x"}, approved=True,
                                      transport=Transport())   # is_production=False
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")


class TestGetStoreInitRetry(unittest.TestCase):
    """server._get_store must NOT cache a failed Postgres init, and must NOT silently downgrade to
    SQLite/in-memory when a DB is configured. Uses a fake `psycopg` module so it runs with no real DB
    (the equivalent against a real Postgres 16 is in the integration run)."""

    def setUp(self):
        self._saved = (server._STORE, server._STORE_BUILT)
        server._STORE, server._STORE_BUILT = None, False
        self._psycopg_saved = sys.modules.get("psycopg")
        self._env_saved = {k: os.environ.get(k) for k in ("DATABASE_URL", "SUPABASE_DB_URL", "AFFOS_INGEST_DB")}
        for k in self._env_saved:
            os.environ.pop(k, None)

    def tearDown(self):
        server._STORE, server._STORE_BUILT = self._saved
        if self._psycopg_saved is not None:
            sys.modules["psycopg"] = self._psycopg_saved
        else:
            sys.modules.pop("psycopg", None)
        for k, v in self._env_saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _install_fake_psycopg(self, connect):
        mod = types.ModuleType("psycopg")
        mod.connect = connect

        class _IntegrityError(Exception):
            pass

        mod.IntegrityError = _IntegrityError
        sys.modules["psycopg"] = mod

    def test_db_unavailable_raises_not_cached_then_recovers(self):
        os.environ["DATABASE_URL"] = "postgresql://unreachable/db"
        calls = {"n": 0}

        def flaky_connect(url):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("connection refused")   # DB down on the first attempt
            return object()                           # DB recovered

        self._install_fake_psycopg(flaky_connect)
        # 1) DB down -> StoreUnavailable, and the failure is NOT cached as a permanent None.
        with self.assertRaises(server.StoreUnavailable):
            server._get_store()
        self.assertFalse(server._STORE_BUILT)
        self.assertIsNone(server._STORE)
        # 2) DB recovered -> the NEXT request initializes the store successfully (retry works).
        st = server._get_store()
        self.assertIsNotNone(st)
        self.assertTrue(server._STORE_BUILT)
        self.assertEqual(calls["n"], 2)               # it re-attempted connect after the failure
        # 3) Built once: a later call returns the same store without reconnecting.
        self.assertIs(server._get_store(), st)
        self.assertEqual(calls["n"], 2)

    def test_configured_db_down_does_not_downgrade_to_sqlite(self):
        os.environ["DATABASE_URL"] = "postgresql://unreachable/db"
        os.environ["AFFOS_INGEST_DB"] = ":memory:"     # present, but must NOT be used while a DB is set

        def always_down(url):
            raise OSError("connection refused")

        self._install_fake_psycopg(always_down)
        with self.assertRaises(server.StoreUnavailable):
            server._get_store()
        self.assertFalse(server._STORE_BUILT)
        self.assertIsNone(server._STORE)               # no silent SQLite/in-memory fallback

    def test_no_db_configured_uses_in_memory_and_caches(self):
        # No DATABASE_URL and no AFFOS_INGEST_DB -> in-memory (None) store, cached as the stable result.
        self.assertIsNone(server._get_store())
        self.assertTrue(server._STORE_BUILT)


if __name__ == "__main__":
    unittest.main()
