"""Storage layer Auth & RBAC — SQLite (PRD-002 §5). 5 bảng + seed."""
from __future__ import annotations

import sqlite3

from rbac import matrix as _matrix

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS roles (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS permissions (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS user_roles (
    user_id TEXT NOT NULL REFERENCES users(id),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id        TEXT PRIMARY KEY,
    user_id   TEXT,
    action    TEXT NOT NULL,
    detail    TEXT DEFAULT '',
    timestamp TEXT NOT NULL
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Seed roles (4 role cố định).
    for name in _matrix.ROLES:
        conn.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (name,))
    # Seed permissions catalog.
    for name in _matrix.ALL_PERMISSIONS:
        conn.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (name,))
    conn.commit()


def role_id(conn: sqlite3.Connection, name: str):
    row = conn.execute("SELECT id FROM roles WHERE name = ?", (name,)).fetchone()
    return row["id"] if row else None
