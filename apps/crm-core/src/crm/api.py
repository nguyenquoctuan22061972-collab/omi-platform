"""Module api (PRD-001 §6) — HTTP router nối các module.

Endpoints (bám đúng PRD, không thêm):
  POST /contacts
  GET  /contacts/{id}
  POST /messages
  GET  /conversations?contact_id=
  POST /pipeline/update

Dùng http.server stdlib. Mỗi tiến trình 1 kết nối SQLite (đường dẫn cấu hình qua
CRM_DB_PATH, mặc định file cục bộ).
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from . import db as _db
from . import contacts as _contacts
from . import conversations as _conversations
from . import pipeline as _pipeline


_CONTACT_ID_RE = re.compile(r"^/contacts/([^/]+)$")


def make_handler(conn):
    """Tạo handler class gắn với 1 kết nối DB (thuận tiện cho test)."""

    class Handler(BaseHTTPRequestHandler):
        # Tắt log ồn khi chạy test.
        def log_message(self, *args):  # noqa: D401
            pass

        def _send(self, code: int, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                return json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return {}

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            m = _CONTACT_ID_RE.match(path)
            if m:
                c = _contacts.get_contact(conn, m.group(1))
                return self._send(200, c) if c else self._send(404, {"error": "not found"})
            if path == "/conversations":
                qs = parse_qs(parsed.query)
                cid = (qs.get("contact_id") or [None])[0]
                return self._send(200, _conversations.list_conversations(conn, cid))
            return self._send(404, {"error": "unknown route"})

        def do_POST(self):
            path = urlparse(self.path).path
            data = self._read_json()
            try:
                if path == "/contacts":
                    c = _contacts.create_contact(
                        conn,
                        name=data.get("name", ""),
                        phone=data.get("phone", ""),
                        email=data.get("email", ""),
                        source=data.get("source", ""),
                        tags=data.get("tags") or [],
                    )
                    return self._send(201, c)
                if path == "/messages":
                    conv = _conversations.add_message(
                        conn,
                        channel=data.get("channel", ""),
                        message=data.get("message", ""),
                        contact_id=data.get("contact_id"),
                        phone=data.get("phone", ""),
                        email=data.get("email", ""),
                    )
                    return self._send(201, conv)
                if path == "/pipeline/update":
                    res = _pipeline.update_stage(
                        conn, data.get("contact_id", ""), data.get("stage", "")
                    )
                    return self._send(200, res)
                return self._send(404, {"error": "unknown route"})
            except _pipeline.InvalidStage as e:
                return self._send(400, {"error": str(e)})
            except ValueError as e:
                return self._send(400, {"error": str(e)})

    return Handler


def create_server(host: str = "0.0.0.0", port: int = 8080, db_path: str | None = None):
    db_path = db_path or os.environ.get("CRM_DB_PATH", "crm_core.db")
    conn = _db.connect(db_path)
    _db.init_db(conn)
    return HTTPServer((host, port), make_handler(conn))
