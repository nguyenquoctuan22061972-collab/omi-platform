"""HTTP router Auth & RBAC (PRD-002). /auth/* + endpoint demo có RBAC."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from auth import db as _db, tokens as _tokens, service as _service, audit as _audit
from rbac import middleware as _mw


def make_handler(conn, secret: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # tắt log ồn
            pass

        def _send(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return {}

        def _token(self):
            return _mw.bearer_from_header(self.headers.get("Authorization", ""))

        def do_POST(self):
            path = urlparse(self.path).path
            d = self._body()
            if path == "/auth/login":
                try:
                    return self._send(200, _service.login(conn, d.get("username", ""),
                                                          d.get("password", ""), secret))
                except _service.AuthError:
                    return self._send(401, {"error": "invalid credentials"})
            if path == "/auth/refresh":
                try:
                    return self._send(200, _service.refresh(conn, d.get("refresh_token", ""), secret))
                except _service.AuthError:
                    return self._send(401, {"error": "invalid refresh token"})
            if path == "/auth/logout":
                uid = None
                tok = self._token()
                if tok:
                    try:
                        uid = _mw.authenticate(tok, secret).get("sub")
                    except _mw.Unauthorized:
                        uid = None
                _service.logout(conn, d.get("refresh_token", ""), user_id=uid)
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "unknown route"})

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/auth/me":
                try:
                    return self._send(200, _service.me(conn, self._token(), secret))
                except Exception:
                    return self._send(401, {"error": "unauthorized"})
            if path == "/contacts":  # demo RBAC: cần contact:read
                try:
                    _mw.require_permission(self._token(), secret, "contact:read")
                    return self._send(200, {"data": []})
                except _mw.Unauthorized:
                    return self._send(401, {"error": "unauthorized"})
                except _mw.Forbidden:
                    claims = None
                    try:
                        claims = _mw.authenticate(self._token(), secret)
                    except _mw.Unauthorized:
                        pass
                    _audit.log(conn, "access_denied",
                               user_id=(claims or {}).get("sub"), detail="contact:read")
                    return self._send(403, {"error": "forbidden"})
            return self._send(404, {"error": "unknown route"})

    return Handler


def create_server(host="0.0.0.0", port=8081, db_path=None, secret=None):
    db_path = db_path or os.environ.get("AUTH_DB_PATH", "auth_rbac.db")
    secret = secret or os.environ.get("AUTH_SECRET", "dev-secret-change-me")
    conn = _db.connect(db_path)
    _db.init_db(conn)
    _tokens.init_store(conn)
    # Seed admin mặc định nếu chưa có (dev).
    if not conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        _service.register(conn, os.environ.get("AUTH_ADMIN_USER", "admin"),
                          os.environ.get("AUTH_ADMIN_PASS", "admin123"), ["Admin"])
    return HTTPServer((host, port), make_handler(conn, secret))
