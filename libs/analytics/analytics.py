"""Analytics Layer (PRD-010 G): event/campaign/attribution/conversion/session.

Provider abstraction (MemoryProvider mặc định). Dry-run — không gửi analytics thật.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Protocol

# Loại event chuẩn.
EVENT_TYPES = {"page_view", "click", "lead", "conversion", "revenue"}


def new_session_id() -> str:
    return "ses_" + uuid.uuid4().hex[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Provider(Protocol):
    def emit(self, event: Dict) -> None: ...


class MemoryProvider:
    def __init__(self):
        self.events: List[Dict] = []

    def emit(self, event: Dict) -> None:
        self.events.append(event)


class Analytics:
    def __init__(self, provider: Provider | None = None, dry_run: bool = True):
        self.provider = provider or MemoryProvider()
        self.dry_run = dry_run

    def _event(self, etype: str, session_id: str, campaign: str, props: Dict) -> Dict:
        if etype not in EVENT_TYPES:
            raise ValueError(f"event không hợp lệ: {etype}. Cho phép: {sorted(EVENT_TYPES)}")
        return {
            "id": "evt_" + uuid.uuid4().hex[:16],
            "ts": _now(),
            "type": etype,
            "session_id": session_id,
            "campaign": campaign,
            "props": props or {},
            "dry_run": self.dry_run,
        }

    def track(self, etype: str, session_id: str, campaign: str = "", **props) -> Dict:
        ev = self._event(etype, session_id, campaign, props)
        self.provider.emit(ev)
        return ev

    # Helpers nghiệp vụ
    def track_revenue(self, session_id: str, amount: float, source: str = "", campaign: str = "") -> Dict:
        return self.track("revenue", session_id, campaign, amount=amount, source=source)

    def track_conversion(self, session_id: str, kind: str = "sale", campaign: str = "") -> Dict:
        return self.track("conversion", session_id, campaign, kind=kind)

    def funnel(self) -> Dict[str, int]:
        """Đếm event theo type (funnel view)."""
        counts = {t: 0 for t in EVENT_TYPES}
        for e in getattr(self.provider, "events", []):
            counts[e["type"]] = counts.get(e["type"], 0) + 1
        return counts

    def attribution(self) -> Dict[str, Dict[str, int]]:
        """Attribution theo campaign: đếm conversion & revenue-event per campaign."""
        out: Dict[str, Dict[str, int]] = {}
        for e in getattr(self.provider, "events", []):
            camp = e.get("campaign") or "(direct)"
            row = out.setdefault(camp, {"conversion": 0, "revenue": 0})
            if e["type"] in row:
                row[e["type"]] += 1
        return out
