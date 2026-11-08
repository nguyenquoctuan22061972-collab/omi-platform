"""AFFOS production runtime HTTP entrypoint (SPRINT 01 — stdlib only).

Exposes a secret-free health endpoint reporting repository mode (DRY-RUN/LIVE).
Start: `python3 runtime/server.py` (PORT from AFFOS_RUNTIME_PORT, default 8099).
Does NOT connect to AWIN or run live transactions. Reading /health does not open a DB
connection (mode is derived from env), so it is safe before credentials exist.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)
import runtime  # noqa: E402

PORT = int(os.environ.get("AFFOS_RUNTIME_PORT", "8099"))


def build_health_response(env=None):
    """Return (status_code, body_bytes) for the health endpoint — unit-testable, no socket."""
    body = json.dumps(runtime.health(env if env is not None else os.environ)).encode()
    return 200, body


def build_output_response(env=None):
    """DRY-RUN first-commercial-output endpoint. Refuses in LIVE mode (returns 409)."""
    import commercial_output
    out = commercial_output.build_output(env if env is not None else os.environ)
    code = 409 if out.get("status") == "REFUSED" else 200
    return code, json.dumps(out, ensure_ascii=False).encode()


def _json_bytes(payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode()


_STORE = None
_STORE_BUILT = False


class StoreUnavailable(RuntimeError):
    """A Postgres store was configured (DATABASE_URL/SUPABASE_DB_URL) but could not be initialized.

    Raised — never cached — so the runtime does NOT silently downgrade to SQLite/in-memory when a DB
    was configured (a must in staging), and so a later request retries once the DB is reachable again.
    """


def _get_store():
    """Durable RevenueStore, built once per process ON SUCCESS. Preference:
      1. Postgres (DATABASE_URL/SUPABASE_DB_URL) — approvals/idempotency/audit live in the 0004/0005
         tables; schema is owned by the migration, so the runtime role does NO DDL here. If the DB is
         configured but UNREACHABLE, raise StoreUnavailable (do NOT cache the failure, do NOT fall back
         to SQLite/in-memory) — the request fails loudly and a later one retries after recovery.
      2. SQLite (AFFOS_INGEST_DB) — durable on a volume for dev/dry-run without a DB.
      3. None — in-memory fallback (pure dry-run), only when no store is configured at all.

    _STORE_BUILT is set True only after a store is successfully built (or no DB is configured), so a
    transient Postgres outage is never cached as a permanent None."""
    global _STORE, _STORE_BUILT
    if _STORE_BUILT:
        return _STORE
    import revenue_store
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if url:
        import psycopg
        try:
            conn = psycopg.connect(url)                 # tables come from migration (no init_schema)
        except Exception as exc:                        # DB configured but down: fail loud, don't cache
            raise StoreUnavailable(
                "DATABASE_URL is configured but the Postgres store is unavailable; refusing to "
                "downgrade to SQLite/in-memory") from exc
        _STORE = revenue_store.RevenueStore(conn, "%s")
        _STORE_BUILT = True                             # mark built ONLY after a successful connect
        return _STORE
    path = os.environ.get("AFFOS_INGEST_DB")
    if path:
        import sqlite3
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        st = revenue_store.RevenueStore(conn, "?")
        st.init_schema(with_commission_unique=False)   # SQLite dev store: create its own tables
        _STORE = st
    _STORE_BUILT = True                                 # no DB configured: cache the stable result
    return _STORE


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _resolve_store(self):
        """Return (store, True), or send a 503 and return (None, False) when a configured DB is down.
        store may legitimately be None (in-memory dry-run) with ok=True when no DB is configured."""
        try:
            return _get_store(), True
        except StoreUnavailable as exc:
            self._send(503, _json_bytes({"error": "store unavailable", "detail": str(exc)}))
            return None, False

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        if parsed.path in ("/health", "/", "/healthz"):
            code, body = build_health_response()
            self._send(code, body)
        elif parsed.path.startswith("/output/dry-run"):
            code, body = build_output_response()
            self._send(code, body)
        elif parsed.path == "/affos/revenue/report":
            import revenue_api
            q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            code, payload = revenue_api.handle_report(q, self.headers, os.environ)
            self._send(code, _json_bytes(payload))
        elif parsed.path == "/affos/revenue/reconcile":
            import revenue_api
            q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            code, payload = revenue_api.handle_reconcile(q, self.headers, os.environ)
            self._send(code, _json_bytes(payload))
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path
        if path == "/affos/revenue/ingest":
            store, ok = self._resolve_store()
            if not ok:
                return
            import revenue_api
            code, payload = revenue_api.handle_ingest(self._read_body(), self.headers, os.environ,
                                                      store=store)
            self._send(code, _json_bytes(payload))
        elif path == "/affos/revenue/approve":
            store, ok = self._resolve_store()
            if not ok:
                return
            import revenue_api
            code, payload = revenue_api.handle_grant(self._read_body(), self.headers, os.environ,
                                                     store=store)
            self._send(code, _json_bytes(payload))
        elif path == "/affos/revenue/approve/revoke":
            store, ok = self._resolve_store()
            if not ok:
                return
            import revenue_api
            code, payload = revenue_api.handle_revoke(self._read_body(), self.headers, os.environ,
                                                      store=store)
            self._send(code, _json_bytes(payload))
        else:
            self._send(404, b'{"error":"not found"}')

    def log_message(self, *args):   # keep logs quiet / no secret leakage
        return


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"affos-runtime listening on :{PORT} (mode={runtime.repository_mode(os.environ)})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
