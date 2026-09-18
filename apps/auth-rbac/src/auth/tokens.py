"""Refresh token store (PRD-002 §3 Refresh/Logout).

Lưu hash refresh token (không lưu bản rõ). MVP: in-memory dict trên connection-scope
được thay bằng bảng phụ đơn giản trong cùng SQLite để bền theo tiến trình test.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3

_STORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    revoked    INTEGER NOT NULL DEFAULT 0
);
"""


def init_store(conn: sqlite3.Connection) -> None:
    conn.executescript(_STORE_SCHEMA)
    conn.commit()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(conn: sqlite3.Connection, user_id: str) -> str:
    """Sinh refresh token mới, lưu hash, trả bản rõ cho client."""
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT OR REPLACE INTO refresh_tokens (token_hash, user_id, revoked) VALUES (?, ?, 0)",
        (_hash(token), user_id),
    )
    conn.commit()
    return token


def resolve(conn: sqlite3.Connection, token: str):
    """Trả user_id nếu refresh token hợp lệ & chưa thu hồi, ngược lại None."""
    row = conn.execute(
        "SELECT user_id, revoked FROM refresh_tokens WHERE token_hash = ?",
        (_hash(token),),
    ).fetchone()
    if not row or row["revoked"]:
        return None
    return row["user_id"]


def revoke(conn: sqlite3.Connection, token: str) -> bool:
    """Thu hồi refresh token (logout). Trả True nếu có tác dụng."""
    cur = conn.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ? AND revoked = 0",
        (_hash(token),),
    )
    conn.commit()
    return cur.rowcount > 0
