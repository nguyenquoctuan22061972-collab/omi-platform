"""Audit actions + retention (PRD-012 B). Additive — không sửa trail.py.

Bổ sung action nghiệp vụ (login, workflow_trigger, publish, rollback) + retention config.
Không log secret (redact qua khoá nghi ngờ).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List

# Action nghiệp vụ (mở rộng, độc lập với trail.EVENTS để không phá test cũ).
ACTIONS = {"login", "logout", "workflow_trigger", "publish", "rollback",
           "deploy", "adapter_enable", "role_change"}

_SECRET_HINTS = ("password", "token", "secret", "api_key", "access_token", "authorization")


def _redact(meta: Dict) -> Dict:
    out = {}
    for k, v in (meta or {}).items():
        out[k] = "***redacted***" if any(h in k.lower() for h in _SECRET_HINTS) else v
    return out


class RetentionPolicy:
    def __init__(self, days: int = 90, max_records: int = 100000):
        self.days = days
        self.max_records = max_records

    def cutoff_iso(self, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        return (now - timedelta(days=self.days)).isoformat()


class ActionLog:
    """Ghi audit theo action + tự prune theo RetentionPolicy. In-memory (sink cắm sau)."""

    def __init__(self, policy: RetentionPolicy | None = None):
        self.policy = policy or RetentionPolicy()
        self.records: List[Dict] = []

    def record(self, action: str, actor: str = "", target: str = "", meta: Dict | None = None) -> Dict:
        if action not in ACTIONS:
            raise ValueError(f"action không hợp lệ: {action}. Cho phép: {sorted(ACTIONS)}")
        rec = {
            "id": "act_" + uuid.uuid4().hex[:16],
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "target": target,
            "meta": _redact(meta or {}),
        }
        self.records.append(rec)
        self._prune()
        return rec

    def _prune(self) -> None:
        cutoff = self.policy.cutoff_iso()
        self.records = [r for r in self.records if r["ts"] >= cutoff][-self.policy.max_records:]

    def by_action(self, action: str) -> List[Dict]:
        return [r for r in self.records if r["action"] == action]
