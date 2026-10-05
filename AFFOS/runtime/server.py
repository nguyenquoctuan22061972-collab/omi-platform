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


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/health", "/", "/healthz"):
            code, body = build_health_response()
            self._send(code, body)
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
