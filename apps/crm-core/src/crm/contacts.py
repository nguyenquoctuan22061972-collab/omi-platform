"""Module contacts (PRD-001 §6, §9.2).

- create_contact: tạo mới, tự MERGE nếu trùng phone HOẶC email.
- get_contact: đọc hồ sơ hợp nhất.
- find_by_phone_or_email: dùng bởi ingestion/conversations để gắn đúng contact.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from . import db as _db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
    return d


def find_by_phone_or_email(
    conn: sqlite3.Connection, phone: str = "", email: str = ""
) -> Optional[dict]:
    """Tìm contact theo phone HOẶC email (chỉ so khớp giá trị khác rỗng)."""
    clauses, params = [], []
    if phone:
        clauses.append("phone = ?")
        params.append(phone)
    if email:
        clauses.append("email = ?")
        params.append(email)
    if not clauses:
        return None
    row = conn.execute(
        f"SELECT * FROM contacts WHERE {' OR '.join(clauses)} LIMIT 1", params
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_contact(conn: sqlite3.Connection, contact_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM contacts WHERE id = ?", (contact_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def _merge_tags(existing: str, new_tags) -> str:
    cur = [t for t in (existing or "").split(",") if t]
    for t in new_tags or []:
        if t and t not in cur:
            cur.append(t)
    return ",".join(cur)


def create_contact(
    conn: sqlite3.Connection,
    name: str = "",
    phone: str = "",
    email: str = "",
    source: str = "",
    tags=None,
) -> dict:
    """Tạo contact; nếu trùng phone/email thì MERGE vào contact có sẵn.

    Merge: điền các trường còn trống, hợp nhất tags, giữ nguyên id & created_at.
    """
    tags = tags or []
    existing = find_by_phone_or_email(conn, phone=phone, email=email)
    if existing:
        cid = existing["id"]
        conn.execute(
            """UPDATE contacts SET
                   name   = CASE WHEN name='' OR name IS NULL THEN ? ELSE name END,
                   phone  = CASE WHEN phone='' OR phone IS NULL THEN ? ELSE phone END,
                   email  = CASE WHEN email='' OR email IS NULL THEN ? ELSE email END,
                   source = CASE WHEN source='' OR source IS NULL THEN ? ELSE source END,
                   tags   = ?
               WHERE id = ?""",
            (
                name,
                phone,
                email,
                source,
                _merge_tags(existing.get("tags") and ",".join(existing["tags"]) or "", tags),
                cid,
            ),
        )
        conn.commit()
        return get_contact(conn, cid)

    cid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO contacts (id, name, phone, email, source, tags, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cid, name, phone, email, source, ",".join(tags), _now()),
    )
    conn.commit()
    return get_contact(conn, cid)


def list_contacts(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT * FROM contacts ORDER BY created_at"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]
