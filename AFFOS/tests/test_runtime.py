"""QA — AFFOS production runtime wiring (SPRINT 01). No prod credentials needed."""
import json
import os
import sys
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


if __name__ == "__main__":
    unittest.main()
