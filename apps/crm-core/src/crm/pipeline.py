"""Module pipeline (PRD-001 §6 /pipeline/update, §7 stages, §10).

Cập nhật giai đoạn bán hàng; chỉ nhận 6 stage hợp lệ theo PRD.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from .models import PIPELINE_STAGES
from . import contacts as _contacts


class InvalidStage(ValueError):
    pass


def update_stage(
    conn: sqlite3.Connection, contact_id: str, stage: str
) -> dict:
    """Đặt/đổi stage cho contact. Stage lạ → InvalidStage. Contact không tồn tại → ValueError."""
    if stage not in PIPELINE_STAGES:
        raise InvalidStage(
            f"Stage không hợp lệ: {stage!r}. Cho phép: {PIPELINE_STAGES}"
        )
    if not _contacts.get_contact(conn, contact_id):
        raise ValueError(f"Contact không tồn tại: {contact_id}")

    conn.execute(
        """INSERT INTO pipeline (contact_id, stage) VALUES (?, ?)
           ON CONFLICT(contact_id) DO UPDATE SET stage = excluded.stage""",
        (contact_id, stage),
    )
    conn.commit()
    return {"contact_id": contact_id, "stage": stage}


def get_stage(conn: sqlite3.Connection, contact_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT stage FROM pipeline WHERE contact_id = ?", (contact_id,)
    ).fetchone()
    return row["stage"] if row else None
