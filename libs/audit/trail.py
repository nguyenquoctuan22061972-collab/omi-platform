"""Audit trail interface (PRD-008 C). Sink pluggable; lọc secret."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Protocol

# Loại sự kiện được audit.
EVENTS = {
    "deploy",
    "login",
    "role_change",
    "workflow_activation",
    "adapter_enable",
    "rollback",
}

# Khoá nghi chứa secret → không ghi.
_SECRET_HINTS = ("password", "token", "secret", "api_key", "access_token", "authorization")


def _sanitize(meta: Dict) -> Dict:
    clean = {}
    for k, v in (meta or {}).items():
        if any(h in k.lower() for h in _SECRET_HINTS):
            clean[k] = "***redacted***"
        else:
            clean[k] = v
    return clean


class Sink(Protocol):
    def write(self, record: Dict) -> None: ...


class MemorySink:
    def __init__(self):
        self.records: List[Dict] = []

    def write(self, record: Dict) -> None:
        self.records.append(record)


class AuditTrail:
    def __init__(self, sink: Sink | None = None):
        self.sink = sink or MemorySink()

    def record(self, event: str, actor: str = "", target: str = "", meta: Dict | None = None) -> Dict:
        if event not in EVENTS:
            raise ValueError(f"event không hợp lệ: {event}. Cho phép: {sorted(EVENTS)}")
        rec = {
            "id": "aud_" + uuid.uuid4().hex[:16],
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "actor": actor,
            "target": target,
            "meta": _sanitize(meta or {}),
        }
        self.sink.write(rec)
        return rec
