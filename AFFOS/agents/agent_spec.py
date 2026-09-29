"""AFFOS Agent spec (PRD-017). Schema validate + permission model (CANNOT overrides CAN)."""
from __future__ import annotations

from typing import Dict, List

FIELDS = ["id", "name", "role", "version", "mission", "input", "output", "skills",
          "permissions", "cost_limit", "kpi", "owner", "status", "last_run", "failure_count"]
STATUSES = {"active", "idle", "failed", "blocked"}


def validate_agent(spec: Dict) -> List[str]:
    errs = []
    for f in FIELDS:
        if f not in spec:
            errs.append(f"thiếu field: {f}")
    if spec.get("status") not in STATUSES:
        errs.append("status không hợp lệ")
    perms = spec.get("permissions", {})
    if not isinstance(perms.get("can"), list) or not isinstance(perms.get("cannot"), list):
        errs.append("permissions cần {can:[], cannot:[]}")
    if not isinstance(spec.get("cost_limit"), (int, float)):
        errs.append("cost_limit phải số")
    return errs


def can(spec: Dict, action: str) -> bool:
    """CANNOT luôn thắng CAN (deny-by-default cho hành động nhạy cảm)."""
    perms = spec.get("permissions", {})
    if action in perms.get("cannot", []):
        return False
    return action in perms.get("can", [])
