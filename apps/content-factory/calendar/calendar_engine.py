"""Content Calendar (PRD-010 E): queue calendar, publish schedule, priority matrix,
retry policy, execution history. Không đổi workflow cũ; thuần trong bộ nhớ.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

# Priority matrix: (nền tảng, độ nóng) → điểm ưu tiên (nhỏ = ưu tiên cao).
PRIORITY_MATRIX = {
    ("youtube", "high"): 1, ("youtube", "normal"): 3,
    ("tiktok", "high"): 2, ("tiktok", "normal"): 4,
    ("facebook", "high"): 3, ("facebook", "normal"): 5,
}
DEFAULT_PRIORITY = 6
MAX_RETRIES = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def priority_of(platform: str, heat: str = "normal") -> int:
    return PRIORITY_MATRIX.get((platform, heat), DEFAULT_PRIORITY)


class ContentCalendar:
    def __init__(self):
        self.items: List[Dict] = []
        self.history: List[Dict] = []

    def schedule(self, title: str, platform: str, publish_at: str, heat: str = "normal") -> Dict:
        item = {
            "id": "cal_" + uuid.uuid4().hex[:12],
            "title": title,
            "platform": platform,
            "publish_at": publish_at,
            "priority": priority_of(platform, heat),
            "status": "scheduled",
            "attempts": 0,
        }
        self.items.append(item)
        return item

    def due(self, now_iso: str) -> List[Dict]:
        """Item tới hạn (publish_at <= now), sắp theo priority."""
        due = [i for i in self.items if i["status"] == "scheduled" and i["publish_at"] <= now_iso]
        return sorted(due, key=lambda i: i["priority"])

    def mark_published(self, item: Dict) -> None:
        item["status"] = "published"
        self.history.append({"id": item["id"], "result": "published", "ts": _now()})

    def mark_failed(self, item: Dict, error: str = "") -> str:
        """Retry policy: còn lượt → scheduled lại; hết → failed."""
        item["attempts"] += 1
        if item["attempts"] < MAX_RETRIES:
            item["status"] = "scheduled"
            self.history.append({"id": item["id"], "result": "retry", "error": error, "ts": _now()})
            return "retry"
        item["status"] = "failed"
        self.history.append({"id": item["id"], "result": "failed", "error": error, "ts": _now()})
        return "failed"

    def stats(self) -> Dict:
        by: Dict[str, int] = {}
        for i in self.items:
            by[i["status"]] = by.get(i["status"], 0) + 1
        return {"total": len(self.items), "by_status": by, "history": len(self.history)}
