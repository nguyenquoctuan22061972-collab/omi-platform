"""Persistent Result Store (AFFOS command path, PRD-013/014 wiring).

Lưu bền vững trạng thái/kết quả của job theo correlation_id. Mirror đúng mẫu
adapter SQLite/Postgres của AFFOS/core/repository.py — KHÔNG đụng schema 21 bảng
của AFFOS core (đây là bảng riêng `job_results` của orchestrator).

- SQLite (mặc định, TEST/DRY_RUN): file hoặc :memory:.
- Postgres (LIVE): inject `conn`, hoặc DSN qua DATABASE_URL/SUPABASE_DB_URL (lazy driver).
- Idempotent: khóa chính correlation_id → retry ghi đè cùng 1 dòng, không trùng.
- KHÔNG lưu secrets: error được scrub trước khi ghi.

Thuần stdlib ở nhánh SQLite; không network.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Mapping, Optional

# Trạng thái vòng đời (khớp directive): QUEUED/RUNNING/SUCCEEDED/FAILED/BLOCKED.
QUEUED = "QUEUED"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
BLOCKED = "BLOCKED"
STATES = {QUEUED, RUNNING, SUCCEEDED, FAILED, BLOCKED}

_COLS = ("correlation_id", "task_id", "command", "target", "status",
         "result_json", "error", "worker", "capability", "created_at", "updated_at")

_DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS job_results (
    correlation_id TEXT PRIMARY KEY,
    task_id TEXT, command TEXT, target TEXT, status TEXT,
    result_json TEXT, error TEXT, worker TEXT, capability TEXT,
    created_at TEXT, updated_at TEXT
);
"""

# Scrub token/secret-like substrings từ error trước khi persist (không lưu dữ liệu nhạy cảm).
_SECRET_RE = re.compile(
    r"(?i)\b(token|secret|password|api[_-]?key|bearer|authorization)\b\s*[:=]\s*\S+"
)
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def scrub(text: Optional[str]) -> str:
    if not text:
        return ""
    t = _SECRET_RE.sub(lambda m: m.group(0).split(m.group(1))[0] + m.group(1) + "=***", text)
    t = _JWT_RE.sub("***", t)
    return t


class ResultStore:
    """job_results store. SQLite mặc định; Postgres khi có conn/DSN (LIVE)."""

    def __init__(self, path: str = ":memory:", conn=None,
                 env: Optional[Mapping[str, str]] = None):
        env = env or {}
        self.backend = "sqlite"
        if conn is not None:
            self.conn = conn
            self.backend = "postgres"
            self._ensure_pg()
            return
        url = env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")
        if url:
            self.conn = self._connect_pg(url)
            self.backend = "postgres"
            self._ensure_pg()
            return
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_DDL_SQLITE)
        self.conn.commit()

    # ---- Postgres helpers (LIVE) ----
    @staticmethod
    def _connect_pg(url: str):
        try:
            import psycopg  # psycopg3
        except ImportError:
            try:
                import psycopg2 as psycopg
            except ImportError:
                raise RuntimeError(
                    "Postgres driver chưa cài (pip install 'psycopg[binary]') — PR-003") from None
        return psycopg.connect(url)

    def _ensure_pg(self) -> None:
        ddl = _DDL_SQLITE  # cùng DDL, tương thích Postgres
        cur = self.conn.cursor()
        cur.execute(ddl.strip().rstrip(";"))
        self.conn.commit()

    # ---- write ----
    def put(self, record: Dict) -> Dict:
        """Upsert theo correlation_id (idempotent). Trả bản ghi đã lưu."""
        cid = record.get("correlation_id")
        if not cid:
            raise ValueError("record cần correlation_id")
        status = record.get("status")
        if status not in STATES:
            raise ValueError(f"status không hợp lệ: {status}")
        existing = self.get(cid)
        now = _now()
        row = {
            "correlation_id": cid,
            "task_id": record.get("task_id") or (existing or {}).get("task_id"),
            "command": record.get("command") or (existing or {}).get("command"),
            "target": record.get("target") or (existing or {}).get("target"),
            "status": status,
            "result_json": json.dumps(record["result"], ensure_ascii=False)
            if record.get("result") is not None
            else (existing or {}).get("result_json"),
            "error": scrub(record.get("error")) or (existing or {}).get("error", ""),
            "worker": record.get("worker") or (existing or {}).get("worker"),
            "capability": record.get("capability") or (existing or {}).get("capability"),
            "created_at": (existing or {}).get("created_at") or now,
            "updated_at": now,
        }
        ph = "?" if self.backend == "sqlite" else "%s"
        cols = ",".join(_COLS)
        placeholders = ",".join([ph] * len(_COLS))
        vals = tuple(row[c] for c in _COLS)
        if self.backend == "sqlite":
            self.conn.execute(
                f"INSERT OR REPLACE INTO job_results ({cols}) VALUES ({placeholders})", vals)
        else:
            upd = ", ".join(f"{c}=EXCLUDED.{c}" for c in _COLS if c != "correlation_id")
            self.conn.execute(
                f"INSERT INTO job_results ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT (correlation_id) DO UPDATE SET {upd}", vals)
        self.conn.commit()
        return self.get(cid)

    # ---- read ----
    def get(self, correlation_id: str) -> Optional[Dict]:
        ph = "?" if self.backend == "sqlite" else "%s"
        cur = self.conn.cursor()
        cur.execute(f"SELECT {','.join(_COLS)} FROM job_results WHERE correlation_id={ph}",
                    (correlation_id,))
        r = cur.fetchone()
        if r is None:
            return None
        d = dict(zip(_COLS, tuple(r)))
        if d.get("result_json"):
            try:
                d["result"] = json.loads(d["result_json"])
            except Exception:
                d["result"] = None
        else:
            d["result"] = None
        return d

    def count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM job_results")
        return cur.fetchone()[0]
