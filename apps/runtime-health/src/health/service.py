"""HealthService (PRD-008 A): aggregate health, deps, uptime, version, build, ready/live.

Không gọi API thật — dependency status suy từ cấu hình env (dry-run).
"""
from __future__ import annotations

import os
import time
from typing import Dict, Mapping

_START = time.time()

# Dependency → env quyết định "configured".
_DEPS = {
    "crm_core": ["CRM_BASE"],
    "auth_rbac": ["AUTH_SECRET"],
    "n8n": ["N8N_BASE_URL"],
}


class HealthService:
    def __init__(self, env: Mapping[str, str] | None = None, start: float | None = None):
        self.env = env if env is not None else os.environ
        self.start = start if start is not None else _START

    def uptime_seconds(self) -> float:
        return round(time.time() - self.start, 3)

    def version(self) -> Dict:
        return {
            "version": self.env.get("APP_VERSION", "0.0.0-dev"),
            "git_sha": self.env.get("GIT_SHA", "unknown"),
        }

    def build_info(self) -> Dict:
        return {
            "build_time": self.env.get("BUILD_TIME", "unknown"),
            "python": os.sys.version.split()[0],
            **self.version(),
        }

    def dependencies(self) -> Dict[str, Dict]:
        out = {}
        for dep, keys in _DEPS.items():
            missing = [k for k in keys if not self.env.get(k)]
            out[dep] = {"configured": not missing, "missing_env": missing}
        return out

    def liveness(self) -> Dict:
        # Process còn sống → live. Không phụ thuộc deps.
        return {"status": "live", "uptime_seconds": self.uptime_seconds()}

    def readiness(self) -> Dict:
        deps = self.dependencies()
        ready = all(d["configured"] for d in deps.values())
        return {"status": "ready" if ready else "not_ready", "dependencies": deps}

    def health(self) -> Dict:
        r = self.readiness()
        return {
            "status": "healthy" if r["status"] == "ready" else "degraded",
            "uptime_seconds": self.uptime_seconds(),
            **self.version(),
            "dependencies": r["dependencies"],
        }
