"""CEO Revenue Dashboard — integration layer (PRD-010 F). File MỚI; không sửa autopilot.py.

Widgets: Today's Revenue · Pipeline Value · Leads · Affiliate Clicks · Content Queue ·
Publish Status · AI Cost (placeholder). Dependency-injected; mock fallback; không API thật.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


class RevenueDashboard:
    def __init__(
        self,
        revenue_overview: Optional[Dict] = None,
        pipeline_value: float = 0.0,
        leads: Optional[List[Dict]] = None,
        affiliate_clicks: int = 0,
        content_queue: Optional[Dict] = None,
        publish_status: Optional[List[Dict]] = None,
    ):
        self.revenue_overview = revenue_overview or {"total": 0.0, "affiliate": 0.0, "lead": 0.0}
        self.pipeline_value = pipeline_value
        self.leads = leads or []
        self.affiliate_clicks = affiliate_clicks
        self.content_queue = content_queue or {"total": 0, "by_status": {}}
        self.publish_status = publish_status or []

    def todays_revenue(self) -> Dict:
        return {"total": self.revenue_overview.get("total", 0.0),
                "affiliate": self.revenue_overview.get("affiliate", 0.0),
                "lead": self.revenue_overview.get("lead", 0.0)}

    def ai_cost_placeholder(self) -> Dict:
        return {"status": "placeholder", "value": None,
                "note": "chờ dữ liệu chi phí AI thật (provider billing)"}

    def dashboard(self) -> Dict:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "todays_revenue": self.todays_revenue(),
            "pipeline_value": self.pipeline_value,
            "leads": len(self.leads),
            "affiliate_clicks": self.affiliate_clicks,
            "content_queue": self.content_queue,
            "publish_status": self.publish_status,
            "ai_cost": self.ai_cost_placeholder(),
        }
