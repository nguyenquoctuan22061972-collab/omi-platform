"""Storage layer — SQLite (PRD-001 §7).

Schema bám đúng PRD:
- contacts(id, name, phone, email, source, tags, created_at)
- conversations(id, contact_id, channel, message, timestamp)
- pipeline(contact_id, stage)  # stage ∈ 6 giá trị PRD
"""
from __future__ import annotations

import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    phone       TEXT,
    email       TEXT,
    source      TEXT,
    tags        TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    contact_id  TEXT NOT NULL,
    channel     TEXT NOT NULL,
    message     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);
CREATE TABLE IF NOT EXISTS pipeline (
    contact_id  TEXT PRIMARY KEY,
    stage       TEXT NOT NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Mở kết nối, bật foreign_keys và row factory dict-like.

    check_same_thread=False: cho phép dùng connection từ luồng phục vụ HTTP
    (server chạy đơn luồng nên không có truy cập song song).
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Tạo schema (idempotent)."""
    conn.executescript(SCHEMA)
    conn.commit()
