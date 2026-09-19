"""Health Gateway (PRD-011 C). Kiểm tra CRM/n8n reachable, adapter, queue status.

Reachability checker INJECTABLE (mặc định urllib timeout ngắn, không bao giờ crash).
Trong test/CI inject stub → không network. Additive: chỉ thêm, không sửa HealthService.
"""
from __future__ import annotations

from typing import Callable, Dict, Mapping, Optional
from urllib.request import urlopen


def _default_checker(url: str, timeout: float = 3.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as r:  # noqa: S310 (URL từ env, không phải input user)
            return 200 <= getattr(r, "status", 200) < 500
    except Exception:
        return False


class HealthGateway:
    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        checker: Optional[Callable[[str], bool]] = None,
        adapter_status: Optional[Dict] = None,
        queue_status: Optional[Dict] = None,
    ):
        self.env = env or {}
        self.checker = checker or _default_checker
        self._adapter_status = adapter_status
        self._queue_status = queue_status

    def _reach(self, base: str, path: str) -> str:
        if not base:
            return "not_configured"
        url = base.rstrip("/") + path
        return "reachable" if self.checker(url) else "unreachable"

    def crm(self) -> Dict:
        return {"target": "crm", "status": self._reach(self.env.get("CRM_BASE", ""), "/dashboard/kpi")}

    def n8n(self) -> Dict:
        return {"target": "n8n", "status": self._reach(self.env.get("N8N_BASE_URL", ""), "/healthz")}

    def adapters(self) -> Dict:
        # Inject từ libs.integrations.activation ở runtime; mặc định dry-run/unknown.
        return self._adapter_status or {"mode": "dry-run", "enabled": 0, "note": "inject activation_report khi wiring"}

    def queue(self) -> Dict:
        return self._queue_status or {"status": "not_wired", "pending": 0, "dead_letter": 0}

    def gateway(self) -> Dict:
        crm, n8n = self.crm(), self.n8n()
        ok = crm["status"] == "reachable" and n8n["status"] == "reachable"
        return {
            "status": "ready" if ok else "degraded",
            "crm": crm,
            "n8n": n8n,
            "adapters": self.adapters(),
            "queue": self.queue(),
        }
