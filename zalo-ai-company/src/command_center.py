"""ZALO AI COMPANY v1.0 — Command Center (PRD-015).

Điều phối 9 phòng ban theo manifest (company.manifest.json). Chỉ đọc/validate + tổng hợp
trạng thái + gom Permission Request. KHÔNG gọi dịch vụ ngoài; thuần stdlib.

Reuse: mỗi department 'runtime_binding' trỏ tới module đã build (orchestrator/libs/apps).
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

HERE = os.path.dirname(__file__)
MANIFEST = os.path.abspath(os.path.join(HERE, "..", "company.manifest.json"))
VALID_STATUS = {"active", "degraded", "blocked"}
VALID_PRIORITY = {"P0", "P1", "P2", "none"}


class CommandCenter:
    def __init__(self, manifest_path: str = MANIFEST):
        with open(manifest_path, encoding="utf-8") as fh:
            self.m = json.load(fh)

    # ---- validate ----
    def validate(self) -> List[str]:
        errs: List[str] = []
        if self.m.get("version") != "1.0":
            errs.append("version != 1.0")
        deps = self.m.get("departments", [])
        ids = [d["id"] for d in deps]
        if len(ids) != 9:
            errs.append(f"cần 9 phòng ban, có {len(ids)}")
        if len(set(ids)) != len(ids):
            errs.append("department id trùng")
        for d in deps:
            if d.get("status") not in VALID_STATUS:
                errs.append(f"{d['id']}: status lạ")
            if d.get("permission") not in VALID_PRIORITY:
                errs.append(f"{d['id']}: permission lạ")
        for pr in self.m.get("permission_requests", []):
            if pr.get("priority") not in ("P0", "P1", "P2"):
                errs.append(f"{pr.get('id')}: priority lạ")
        return errs

    # ---- queries ----
    def departments(self) -> List[Dict]:
        return self.m["departments"]

    def by_status(self, status: str) -> List[str]:
        return [d["id"] for d in self.m["departments"] if d["status"] == status]

    def permission_requests(self, priority: str | None = None) -> List[Dict]:
        prs = self.m.get("permission_requests", [])
        return [p for p in prs if priority is None or p["priority"] == priority]

    def readiness(self) -> Dict:
        deps = self.m["departments"]
        active = self.by_status("active")
        blocked = self.by_status("blocked")
        degraded = self.by_status("degraded")
        return {
            "project": self.m["project"], "version": self.m["version"],
            "total": len(deps), "active": len(active), "degraded": len(degraded),
            "blocked": len(blocked),
            "active_pct": round(100.0 * len(active) / len(deps), 1) if deps else 0.0,
            "open_permissions": {p: len(self.permission_requests(p)) for p in ("P0", "P1", "P2")},
            "blocked_departments": blocked, "degraded_departments": degraded,
        }
