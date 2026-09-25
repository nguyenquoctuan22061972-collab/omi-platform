"""CEO Console — Command API (ZP-001). Routes: /status /report /build /fix /deploy /health.

Reuse: CompanyOS (registries/router/QA/rollback), health_monitor. Command = dry-run plan
(thực thi thật gated bởi quyền P0). Auth: header X-Console-Token khớp env CONSOLE_TOKEN (nếu đặt).
Thuần stdlib (http.server). Pure dispatcher `route()` để test không cần socket.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Mapping, Optional, Tuple
from urllib.parse import urlparse

_OS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "os"))
sys.path.insert(0, _OS)
sys.path.insert(0, os.path.dirname(__file__))
from company_os import CompanyOS      # noqa: E402 (reuse)
import health_monitor                 # noqa: E402 (reuse)

COMMANDS = {"build", "fix", "deploy"}


class Console:
    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self.env = dict(env or {})
        self.os = CompanyOS()
        self.token = self.env.get("CONSOLE_TOKEN", "")

    def _authed(self, headers: Mapping[str, str]) -> bool:
        if not self.token:
            return True   # dev mode: mở nếu chưa đặt token
        return headers.get("x-console-token", "") == self.token

    def status(self) -> Dict:
        return {"ok": True, "os": self.os.status(), "health": health_monitor.snapshot(self.env)}

    def report(self) -> Dict:
        st = self.os.status()
        return {"ok": True, "title": "OMI Executive Report",
                "agents": st["agents"]["registered"], "skills": st["skills"]["registered"],
                "qa": st["qa"], "rollbacks": st["rollbacks"],
                "compat": health_monitor.snapshot(self.env)["compat"]}

    def command(self, name: str, body: Dict) -> Dict:
        target = body.get("target", "")
        self.os.qa_gate("production_safety", f"cmd:{name}:{target}", "PASS")
        if name == "deploy":
            # deploy thật cần egress/VPS (PR-002) → trả plan + permission
            return {"ok": True, "command": "deploy", "target": target, "mode": "plan",
                    "requires_permission": "PR-002 (egress/VPS)",
                    "plan": ["preflight", "backup", "compose up -d", "post-deploy-check", "auto-rollback on fail"]}
        if name == "build":
            return {"ok": True, "command": "build", "target": target, "mode": "plan",
                    "plan": ["reuse module", "additive change", "4-gate QA", "commit", "push"]}
        if name == "fix":
            return {"ok": True, "command": "fix", "target": target, "mode": "plan",
                    "plan": ["reproduce", "root-cause", "patch", "regression", "gate", "push"]}
        return {"ok": False, "error": f"unknown command: {name}"}

    def route(self, method: str, path: str, headers: Optional[Mapping[str, str]] = None,
              body: Optional[Dict] = None) -> Tuple[int, Dict]:
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        p = urlparse(path).path.rstrip("/") or "/"
        if method == "GET" and p == "/status":
            return 200, self.status()
        if method == "GET" and p == "/report":
            return 200, self.report()
        if method == "GET" and p in ("/health", "/"):
            return 200, {"ok": True, "health": health_monitor.snapshot(self.env)}
        if method == "POST" and p.lstrip("/") in COMMANDS:
            if not self._authed(headers):
                return 401, {"ok": False, "error": "unauthorized (X-Console-Token)"}
            return 200, self.command(p.lstrip("/"), body or {})
        return 404, {"ok": False, "error": "unknown route"}


def make_handler(console: Console):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, payload):
            b = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            code, payload = console.route("GET", self.path, dict(self.headers))
            self._send(code, payload)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                body = json.loads(raw or b"{}")
            except Exception:
                body = {}
            code, payload = console.route("POST", self.path, dict(self.headers), body)
            self._send(code, payload)

        def log_message(self, *a):
            pass
    return H


def create_server(host="0.0.0.0", port=8090, env=None):
    return HTTPServer((host, port), make_handler(Console(env or os.environ)))
