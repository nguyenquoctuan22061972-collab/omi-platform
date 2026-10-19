"""CEO Console — Command API (ZP-001). Routes: /status /report /build /fix /deploy /health
plus GET /result/{correlation_id}.

Reuse: CompanyOS (registries/router/QA/rollback), health_monitor, and the existing
orchestrator command path (CommandHub → QueueOrchestrator → Worker → ResultStore).
Command mặc định = dry-run plan (preview). Chỉ khi body {"execute": true} mới chạy THẬT qua
orchestrator: mint task_id/correlation_id → enqueue → worker → kết quả lưu bền vững; đọc lại
bằng GET /result/{correlation_id}. deploy LUÔN plan-only (gated PR-002). Auth: header
X-Console-Token khớp env CONSOLE_TOKEN (nếu đặt). Thuần stdlib (http.server). Pure dispatcher
`route()` để test không cần socket.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Mapping, Optional, Tuple
from urllib.parse import urlparse

_OS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "os"))
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _OS)
sys.path.insert(0, os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from company_os import CompanyOS      # noqa: E402 (reuse)
import health_monitor                 # noqa: E402 (reuse)

COMMANDS = {"build", "fix", "deploy"}
EXECUTABLE = {"build", "fix"}          # deploy KHÔNG execute ở đây (gated PR-002)


class Console:
    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self.env = dict(env or {})
        self.os = CompanyOS()
        self.token = self.env.get("CONSOLE_TOKEN", "")
        self._hub = None   # lazy: orchestrator CommandHub (only when execute is used)

    def _hub_(self):
        if self._hub is None:
            from orchestrator.runtime.command_hub import CommandHub
            self._hub = CommandHub(env=self.env)
        return self._hub

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
        execute = bool(body.get("execute"))
        self.os.qa_gate("production_safety", f"cmd:{name}:{target}", "PASS")
        # EXECUTE: chạy thật qua orchestrator command path (không trả mode=plan).
        if execute and name in EXECUTABLE:
            kw = {}
            if body.get("task_id"):
                kw["task_id"] = str(body["task_id"])
            if body.get("correlation_id"):
                kw["correlation_id"] = str(body["correlation_id"])
            sub = self._hub_().run(name, target, **kw)
            out = {"ok": sub.get("status") == "SUCCEEDED", "command": name, "target": target,
                   "mode": "execute", "status": sub.get("status"),
                   "task_id": sub.get("task_id"), "correlation_id": sub.get("correlation_id"),
                   "result": sub.get("result")}
            if sub.get("error"):
                out["error"] = sub["error"]
            return out
        # PLAN/PREVIEW (mặc định): chỉ lập kế hoạch, không thực thi.
        if name == "deploy":
            # deploy thật cần egress/VPS (PR-002) → luôn plan + permission (không execute ở đây)
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

    def result(self, correlation_id: str) -> Tuple[int, Dict]:
        """Đọc lại kết quả bền vững theo correlation_id (CEO Console receiver)."""
        rec = self._hub_().result(correlation_id)
        if rec is None:
            return 404, {"ok": False, "error": "result not found", "correlation_id": correlation_id}
        return 200, {"ok": True, "correlation_id": correlation_id, "task_id": rec.get("task_id"),
                     "command": rec.get("command"), "target": rec.get("target"),
                     "status": rec.get("status"), "result": rec.get("result"),
                     "error": rec.get("error", ""), "worker": rec.get("worker"),
                     "capability": rec.get("capability"), "created_at": rec.get("created_at"),
                     "updated_at": rec.get("updated_at")}

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
        if method == "GET" and p.startswith("/result/"):
            if not self._authed(headers):
                return 401, {"ok": False, "error": "unauthorized (X-Console-Token)"}
            cid = p[len("/result/"):]
            if not cid:
                return 404, {"ok": False, "error": "result not found"}
            return self.result(cid)
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
