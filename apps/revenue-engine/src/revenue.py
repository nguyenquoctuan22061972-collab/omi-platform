"""Revenue Engine (PRD-010 A + resume Step4). Mock/dry-run — KHÔNG thanh toán/API thật.

Gồm: revenue registry · overview/RPM/affiliate/lead/trend/attribution ·
payout abstraction · conversion tracking · affiliate click pipeline · event dispatcher.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict, List

SOURCES = ("affiliate", "lead", "adsense", "other")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RevenueRegistry:
    """Ghi nhận khoản doanh thu (mock). id + source + amount + month."""

    def __init__(self):
        self.entries: List[Dict] = []

    def record(self, source: str, amount: float, month: str = "", meta: Dict | None = None) -> Dict:
        rec = {
            "id": "rev_" + uuid.uuid4().hex[:12],
            "ts": _now(),
            "source": source,
            "amount": float(amount),
            "month": month or datetime.now(timezone.utc).strftime("%Y-%m"),
            "meta": meta or {},
        }
        self.entries.append(rec)
        return rec

    def total(self, source: str | None = None) -> float:
        return round(sum(e["amount"] for e in self.entries
                         if source is None or e["source"] == source), 2)

    def overview(self) -> Dict:
        return {
            "total": self.total(),
            "affiliate": self.total("affiliate"),
            "lead": self.total("lead"),
            "rpm_placeholder": None,  # cần dữ liệu views thật để tính RPM
            "sources": self.source_attribution(),
            "monthly_trend": self.monthly_trend(),
        }

    def source_attribution(self) -> Dict[str, float]:
        agg: Dict[str, float] = defaultdict(float)
        for e in self.entries:
            agg[e["source"]] += e["amount"]
        return {k: round(v, 2) for k, v in agg.items()}

    def monthly_trend(self) -> Dict[str, float]:
        agg: Dict[str, float] = defaultdict(float)
        for e in self.entries:
            agg[e["month"]] += e["amount"]
        return {k: round(v, 2) for k, v in sorted(agg.items())}


class PayoutAbstraction:
    """Trừu tượng payout — KHÔNG thực hiện thanh toán thật."""

    def request_payout(self, amount: float, method: str = "bank") -> Dict:
        return {"status": "dry-run", "amount": float(amount), "method": method,
                "note": "không thực hiện thanh toán thật — cần cổng payout + credential"}


class ConversionTracker:
    def __init__(self):
        self.conversions: List[Dict] = []

    def track(self, click_id: str, value: float = 0.0, kind: str = "sale") -> Dict:
        c = {"id": "cnv_" + uuid.uuid4().hex[:12], "click_id": click_id,
             "value": float(value), "kind": kind, "ts": _now()}
        self.conversions.append(c)
        return c

    def rate(self, total_clicks: int) -> float:
        return round(len(self.conversions) / total_clicks, 4) if total_clicks else 0.0


class AffiliateClickPipeline:
    """Ghi click affiliate → (mock) chuyển hoá thành conversion. Không gọi network."""

    def __init__(self, conversions: ConversionTracker | None = None):
        self.clicks: List[Dict] = []
        self.conversions = conversions or ConversionTracker()

    def record_click(self, network: str, campaign: str = "", session_id: str = "") -> Dict:
        click = {"id": "clk_" + uuid.uuid4().hex[:12], "network": network,
                 "campaign": campaign, "session_id": session_id, "ts": _now()}
        self.clicks.append(click)
        return click

    def convert(self, click_id: str, value: float) -> Dict:
        return self.conversions.track(click_id, value=value)

    def stats(self) -> Dict:
        return {"clicks": len(self.clicks),
                "conversions": len(self.conversions.conversions),
                "cvr": self.conversions.rate(len(self.clicks))}


class RevenueEventDispatcher:
    """Phát revenue event tới các sink đã đăng ký (dry-run; sink là callable)."""

    def __init__(self):
        self._sinks: List[Callable[[Dict], None]] = []
        self.dispatched: List[Dict] = []

    def subscribe(self, sink: Callable[[Dict], None]) -> None:
        self._sinks.append(sink)

    def dispatch(self, event: Dict) -> Dict:
        ev = {"id": "rde_" + uuid.uuid4().hex[:12], "ts": _now(), **event, "dry_run": True}
        for s in self._sinks:
            s(ev)
        self.dispatched.append(ev)
        return ev
