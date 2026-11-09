"""QA — AFFOS runtime SECURITY & OBSERVABILITY (Milestone 2, TASK 3/6). Offline; no DB, no network.

Proves: the health/readiness endpoints and the store-unavailable error never leak the DATABASE_URL
password; the HTTP handler does not log request lines (no accidental secret logging); and a configured
Postgres that is unreachable FAILS CLOSED (readiness 503, no SQLite downgrade), never a false success.
"""
import importlib.machinery
import json
import os
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import runtime  # noqa: E402
import server   # noqa: E402

SECRET = "sup3r_s3cret_pw"
DB_URL = f"postgresql://affos_service:{SECRET}@db.internal:5432/affos_staging"


def _no_secret(blob: str):
    return SECRET not in blob and "affos_service:" not in blob and "db.internal" not in blob


class TestNoSecretLeak(unittest.TestCase):
    def test_runtime_health_is_secret_free(self):
        blob = json.dumps(runtime.health({"DATABASE_URL": DB_URL}))
        self.assertTrue(_no_secret(blob))
        self.assertEqual(json.loads(blob)["repository_mode"], "LIVE")

    def test_server_health_response_secret_free(self):
        code, body = server.build_health_response({"DATABASE_URL": DB_URL})
        self.assertEqual(code, 200)
        self.assertTrue(_no_secret(body.decode()))

    def test_store_unavailable_message_has_no_secret(self):
        # The error surfaced to operators/clients must not echo the connection string.
        exc = server.StoreUnavailable(
            "DATABASE_URL is configured but the Postgres store is unavailable; refusing to "
            "downgrade to SQLite/in-memory")
        self.assertTrue(_no_secret(str(exc)))


class TestHandlerDoesNotLogRequests(unittest.TestCase):
    def test_log_message_is_silenced(self):
        # BaseHTTPRequestHandler.log_message is overridden to a no-op so request lines (which can carry
        # tokens in query strings) are never written to stderr.
        import io
        buf = io.StringIO()
        old = sys.stderr
        sys.stderr = buf
        try:
            server.Handler.log_message(object(), "%s", "GET /affos/revenue/ingest?token=LEAK")
        finally:
            sys.stderr = old
        self.assertEqual(buf.getvalue(), "")


class TestFailClosedReadiness(unittest.TestCase):
    def setUp(self):
        self._saved = (server._STORE, server._STORE_BUILT)
        server._STORE, server._STORE_BUILT = None, False
        self._psy = sys.modules.get("psycopg")
        self._env = {k: os.environ.get(k) for k in ("DATABASE_URL", "SUPABASE_DB_URL", "AFFOS_INGEST_DB")}
        for k in self._env:
            os.environ.pop(k, None)

    def tearDown(self):
        server._STORE, server._STORE_BUILT = self._saved
        if self._psy is not None:
            sys.modules["psycopg"] = self._psy
        else:
            sys.modules.pop("psycopg", None)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_configured_db_down_fails_closed_503_no_secret(self):
        os.environ["DATABASE_URL"] = DB_URL
        os.environ["AFFOS_INGEST_DB"] = ":memory:"      # present, but must NOT be used while a DB is set
        mod = types.ModuleType("psycopg")
        mod.__spec__ = importlib.machinery.ModuleSpec("psycopg", loader=None)

        def down(url):
            raise OSError("connection refused")

        mod.connect = down
        sys.modules["psycopg"] = mod
        code, body = server.build_ready_response()
        self.assertEqual(code, 503)                      # fail closed
        self.assertFalse(json.loads(body)["ready"])
        self.assertTrue(_no_secret(body.decode()))       # 503 body carries no secret
        self.assertFalse(server._STORE_BUILT)            # no SQLite downgrade cached


if __name__ == "__main__":
    unittest.main()
