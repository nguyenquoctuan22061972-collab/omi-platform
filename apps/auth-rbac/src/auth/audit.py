"""Audit log writer (PRD-002 §3 Audit Log)."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Optional


def log(
    conn: sqlite3.Connection,
    action: str,
    user_id: Optional[str] = None,
    detail: str = "",
) -> None:
    conn.execute(
        "INSERT INTO audit_logs (id, user_id, action, detail, timestamp) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, action, detail, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def list_logs(conn: sqlite3.Connection, user_id: Optional[str] = None) -> List[dict]:
    if user_id:
        rows = conn.execute(
            "SELECT * FROM audit_logs WHERE user_id = ? ORDER BY timestamp", (user_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp").fetchall()
    return [dict(r) for r in rows]
