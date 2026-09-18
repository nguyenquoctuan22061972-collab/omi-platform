"""Module dashboard (PRD-001 §5 Dashboard KPI, §10 "KPI realtime").

Đọc trực tiếp DB tại thời điểm gọi (không cache) → phản ánh tức thời.
"""
from __future__ import annotations

import sqlite3

from .models import PIPELINE_STAGES


def kpi(conn: sqlite3.Connection) -> dict:
    """Tổng hợp KPI realtime cho dashboard."""
    total_contacts = conn.execute(
        "SELECT COUNT(*) AS c FROM contacts"
    ).fetchone()["c"]
    total_messages = conn.execute(
        "SELECT COUNT(*) AS c FROM conversations"
    ).fetchone()["c"]

    by_stage = {s: 0 for s in PIPELINE_STAGES}
    for row in conn.execute(
        "SELECT stage, COUNT(*) AS c FROM pipeline GROUP BY stage"
    ).fetchall():
        if row["stage"] in by_stage:
            by_stage[row["stage"]] = row["c"]

    won = by_stage["won"]
    closed = by_stage["won"] + by_stage["lost"]
    win_rate = round(won / closed, 4) if closed else 0.0

    return {
        "total_contacts": total_contacts,
        "total_messages": total_messages,
        "pipeline_by_stage": by_stage,
        "win_rate": win_rate,
    }
