"""HTTP router cho Runtime Health (PRD-008 A). Endpoints MỚI, không đụng endpoint cũ."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from health.service import HealthService
from health.gateway import HealthGateway


def make_handler(svc: HealthService, gateway: "HealthGateway | None" = None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, code, text):
            body = text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _metrics_text(self):
            # Prometheus exposition tối giản, self-contained (PRD-012 A). Không phụ thuộc lib ngoài.
            h = svc.health()
            ready = 1 if h.get("status") == "healthy" else 0
            lines = [
                "# TYPE omi_health_summary gauge",
                f"omi_health_summary {ready}",
                "# TYPE omi_uptime_seconds gauge",
                f"omi_uptime_seconds {svc.uptime_seconds()}",
            ]
            return "\n".join(lines) + "\n"

        def do_GET(self):
            path = urlparse(self.path).path
            routes = {
                "/health": svc.health,
                "/health/live": svc.liveness,
                "/health/ready": svc.readiness,
                "/version": svc.version,
                "/build-info": svc.build_info,
            }
            if path in routes:
                payload = routes[path]()
                # readiness chưa sẵn sàng → 503 để orchestrator biết.
                code = 503 if path == "/health/ready" and payload.get("status") != "ready" else 200
                return self._send(code, payload)
            if path == "/metrics":  # PRD-012 A (endpoint mới, text/plain)
                return self._send_text(200, self._metrics_text())
            if path == "/health/gateway":  # PRD-011 C (endpoint mới)
                gw = gateway or HealthGateway(env=svc.env)
                payload = gw.gateway()
                code = 200 if payload.get("status") == "ready" else 503
                return self._send(code, payload)
            return self._send(404, {"error": "unknown route"})

    return Handler


def create_server(host="0.0.0.0", port=8082, env=None, gateway=None):
    e = env if env is not None else os.environ
    svc = HealthService(env=e)
    return HTTPServer((host, port), make_handler(svc, gateway))
