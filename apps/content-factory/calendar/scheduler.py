"""Nối ContentCalendar (PRD-010 E) → JobQueue (PRD-009 A): lên lịch tập hàng loạt cho
nhiều kênh rồi đẩy job render vào hàng đợi khi tới hạn.

Không render tại đây — chỉ sinh job `render_episode` (payload: channel/episode/publish_at)
để worker xử lý. Thuần stdlib + tái dùng calendar/queue sẵn có (không fork).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _p in (_ROOT, _HERE, os.path.join(_ROOT, "apps", "content-factory", "queue")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from calendar_engine import ContentCalendar, priority_of  # noqa: E402
from jobqueue import JobQueue, Job  # noqa: E402

# libs/video channels (preset 10 kênh)
from libs.video import list_keys, get_channel  # noqa: E402

JOB_KIND = "render_episode"


def seed_week(calendar: ContentCalendar, start_iso: str,
              channels: Optional[List[str]] = None,
              platform: str = "youtube", hour: str = "T09:00:00Z") -> List[Dict]:
    """Lên lịch 1 tập/kênh trong tuần (mỗi kênh 1 ngày, xoay vòng). start_iso = 'YYYY-MM-DD'."""
    import datetime as dt
    channels = channels or list_keys()
    base = dt.date.fromisoformat(start_iso)
    items = []
    for i, key in enumerate(channels):
        ch = get_channel(key)
        day = (base + dt.timedelta(days=i)).isoformat()
        publish_at = f"{day}{hour}"
        it = calendar.schedule(title=f"{ch.brand} — Tập 01", platform=platform,
                               publish_at=publish_at, heat="normal")
        it["channel"] = key
        items.append(it)
    return items


def enqueue_due(calendar: ContentCalendar, queue: JobQueue, now_iso: str,
                episode_no: int = 1) -> List[str]:
    """Với mỗi item tới hạn: tạo Job render_episode đẩy vào queue. Trả list job id."""
    ids: List[str] = []
    for item in calendar.due(now_iso):
        channel = item.get("channel") or _infer_channel(item.get("title", ""))
        payload = {"channel": channel, "episode_no": episode_no,
                   "title": item.get("title", ""),
                   "publish_at": item.get("publish_at", "")}
        job = Job(kind=JOB_KIND, payload=payload,
                  priority=priority_of(item.get("platform", "youtube"),
                                       item.get("heat", "normal")))
        ids.append(queue.enqueue(job))
        calendar.mark_published(item)   # đã chuyển thành job → coi như đã xử lý khỏi lịch
    return ids


def _infer_channel(title: str) -> str:
    t = (title or "").lower()
    for key in list_keys():
        ch = get_channel(key)
        if ch.brand.lower() in t or key in t:
            return key
    return list_keys()[0]
