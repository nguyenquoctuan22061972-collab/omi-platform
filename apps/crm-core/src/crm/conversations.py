"""Module conversations (PRD-001 §6, §10 "Tin nhắn đúng contact").

Ghi message gắn ĐÚNG contact và đọc timeline hội thoại.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from . import contacts as _contacts


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_message(
    conn: sqlite3.Connection,
    channel: str,
    message: str,
    contact_id: Optional[str] = None,
    phone: str = "",
    email: str = "",
) -> dict:
    """Thêm tin nhắn. Resolve contact theo id, hoặc theo phone/email.

    Nếu không tìm được contact và có phone/email → tạo/merge contact mới.
    Đảm bảo message luôn gắn đúng 1 contact tồn tại.
    """
    resolved_id = None
    if contact_id and _contacts.get_contact(conn, contact_id):
        resolved_id = contact_id
    else:
        found = _contacts.find_by_phone_or_email(conn, phone=phone, email=email)
        if found:
            resolved_id = found["id"]
        elif phone or email:
            resolved_id = _contacts.create_contact(
                conn, phone=phone, email=email, source=channel
            )["id"]

    if not resolved_id:
        raise ValueError("Không xác định được contact cho message (thiếu contact_id/phone/email)")

    mid = str(uuid.uuid4())
    ts = _now()
    conn.execute(
        """INSERT INTO conversations (id, contact_id, channel, message, timestamp)
           VALUES (?, ?, ?, ?, ?)""",
        (mid, resolved_id, channel, message, ts),
    )
    conn.commit()
    return {
        "id": mid,
        "contact_id": resolved_id,
        "channel": channel,
        "message": message,
        "timestamp": ts,
    }


def list_conversations(
    conn: sqlite3.Connection, contact_id: Optional[str] = None
) -> list:
    """Timeline hội thoại; lọc theo contact_id nếu có."""
    if contact_id:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE contact_id = ? ORDER BY timestamp",
            (contact_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY timestamp"
        ).fetchall()
    return [dict(r) for r in rows]
