"""CEO Console — Health Monitor (ZP-001). Tổng hợp VPS/Docker/n8n + compat.
Reuse compat_check. Live docker/vps cần shell VPS (đánh dấu requires_vps). Không network."""
from __future__ import annotations

import os
import sys
from typing import Dict, Mapping, Optional

_OS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "os"))
sys.path.insert(0, _OS)
import compat_check  # noqa: E402 (reuse)

EXPECTED_SERVICES = ["crm-core", "auth-rbac", "n8n", "postgres", "nginx"]


def snapshot(env: Optional[Mapping[str, str]] = None) -> Dict:
    env = env or {}
    compat = compat_check.report(["WF004.n8n.json", "WF005.n8n.json"])
    return {
        "compat": compat["compatible"],
        "infra_files": compat["infra"],
        "expected_services": EXPECTED_SERVICES,
        "live_probe": "requires_vps",   # docker ps/nginx -t cần shell VPS (PR-002)
        "workflows": [{"name": w["workflow"], "nodes": w["nodes"], "retry": w["has_retry"]}
                      for w in compat["workflows"]],
    }
