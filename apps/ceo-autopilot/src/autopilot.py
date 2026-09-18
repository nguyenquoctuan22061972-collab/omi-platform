"""CEO Autopilot — integration layer (PRD-009 F).

Tổng hợp dashboard điều hành từ các nguồn (inject vào; mock fallback). KHÔNG gọi API thật.
Widgets: Morning Brief · Daily Priorities · Workflow Health · Revenue (placeholder) ·
AI Queue · Alerts · Approval Center.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CEOAutopilot:
    def __init__(
        self,
        kpi: Optional[Dict] = None,
        queue_stats: Optional[Dict] = None,
        workflow_status: Optional[List[Dict]] = None,
        alerts: Optional[List[Dict]] = None,
        approvals: Optional[List[Dict]] = None,
    ):
        self.kpi = kpi or {"total_contacts": 0, "total_messages": 0, "win_rate": 0.0}
        self.queue_stats = queue_stats or {"total": 0, "by_status": {}, "dead_letter": 0}
        self.workflow_status = workflow_status or []
        self.alerts = alerts or []
        self.approvals = approvals or []

    def morning_brief(self) -> Dict:
        return {
            "generated_at": _now(),
            "contacts": self.kpi.get("total_contacts", 0),
            "messages": self.kpi.get("total_messages", 0),
            "win_rate": self.kpi.get("win_rate", 0.0),
            "open_alerts": len(self.alerts),
            "pending_approvals": len(self.approvals),
        }

    def daily_priorities(self) -> List[str]:
        pri: List[str] = []
        if self.approvals:
            pri.append(f"Duyệt {len(self.approvals)} mục chờ approval")
        if self.alerts:
            pri.append(f"Xử lý {len(self.alerts)} alert")
        if self.queue_stats.get("dead_letter", 0):
            pri.append(f"Kiểm {self.queue_stats['dead_letter']} job dead-letter")
        if not pri:
            pri.append("Không có việc khẩn — review KPI & pipeline")
        return pri

    def workflow_health(self) -> Dict:
        total = len(self.workflow_status)
        active = sum(1 for w in self.workflow_status if w.get("activation") == "importable")
        return {"total": total, "ready": active,
                "planned": sum(1 for w in self.workflow_status if w.get("planned"))}

    def revenue_placeholder(self) -> Dict:
        return {"status": "placeholder", "value": None,
                "note": "chờ nguồn doanh thu thật (PRD sau)"}

    def ai_queue(self) -> Dict:
        return self.queue_stats

    def approval_center(self) -> List[Dict]:
        return self.approvals

    def dashboard(self) -> Dict:
        return {
            "morning_brief": self.morning_brief(),
            "daily_priorities": self.daily_priorities(),
            "workflow_health": self.workflow_health(),
            "revenue": self.revenue_placeholder(),
            "ai_queue": self.ai_queue(),
            "alerts": self.alerts,
            "approval_center": self.approval_center(),
        }
