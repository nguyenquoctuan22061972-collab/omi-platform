"""AFFOS Repository interface + adapters (PRD-017 / CTO review).

- Repository: giao diện chung.
- SqliteRepository: CHỈ cho TEST/DRY_RUN/SEEDED. Từ chối LIVE/PRODUCTION_VERIFIED.
- PostgresRepository: adapter LIVE (Supabase/Postgres). Gated — cần DATABASE_URL/SUPABASE.
  Chưa bật driver mạng trong repo (PR-003); khởi tạo khi thiếu credential → raise.

select_repository(env): trả adapter đúng theo môi trường. KHÔNG bao giờ dùng SQLite cho LIVE.
"""
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Mapping, Optional

sys.path.insert(0, os.path.dirname(__file__))
from data_access import Repo as _SqliteRepo, CHAIN_TABLES, PROV_TABLES   # noqa: E402

_LIVE_STATES = {"LIVE", "PRODUCTION_VERIFIED"}


class Repository(ABC):
    data_state_scope: set = set()

    @abstractmethod
    def insert(self, table: str, row: Dict) -> None: ...
    @abstractmethod
    def query(self, sql: str, params: tuple = ()) -> List[Dict]: ...
    @abstractmethod
    def count(self, table: str) -> int: ...


class SqliteRepository(Repository):
    """TEST/DRY_RUN adapter — KHÔNG dùng cho production."""
    data_state_scope = {"TEST", "DRY_RUN", "SEEDED"}

    def __init__(self, path: str = ":memory:", data_state: str = "DRY_RUN"):
        if data_state not in self.data_state_scope:
            raise ValueError(f"SqliteRepository chỉ cho {self.data_state_scope}, không {data_state}")
        self._r = _SqliteRepo(path, data_state=data_state)
        self.data_state = data_state

    def insert(self, table: str, row: Dict) -> None:
        self._r.insert(table, row)

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        return self._r.query(sql, params)

    def count(self, table: str) -> int:
        return self._r.count(table)


class PostgresRepository(Repository):
    """LIVE adapter (Supabase/Postgres) — MINIMUM functionality for the revenue pipeline.

    Reuses the existing 27-table AffOS model (no schema redesign). Uses the 27-table
    Postgres DDL already in core/schema; this class only issues insert/query/count.
    - Connection: a live psycopg connection built from DATABASE_URL/SUPABASE_DB_URL,
      OR an injected `conn` (for tests / a pre-opened pool). Driver is imported lazily;
      if absent the error is explicit and actionable (never a silent SQLite fallback).
    - Economic truth: only LIVE/PRODUCTION_VERIFIED data_state is accepted on provenance
      tables; TEST/DRY_RUN/SEEDED is refused here (that belongs to SqliteRepository).
    Placeholders are %s (psycopg paramstyle); upsert mirrors SQLite's INSERT OR REPLACE.
    """
    data_state_scope = _LIVE_STATES

    def __init__(self, env: Optional[Mapping[str, str]] = None,
                 conn=None, data_state: str = "LIVE"):
        if data_state not in self.data_state_scope:
            raise ValueError(f"PostgresRepository chỉ cho {self.data_state_scope}, không {data_state}")
        self.data_state = data_state
        if conn is not None:
            self.conn = conn                       # injected (tests / pre-opened connection)
            return
        env = env or {}
        url = env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")
        if not url:
            raise RuntimeError("PostgresRepository cần DATABASE_URL/SUPABASE_DB_URL (PR-003) — chưa cấp")
        self.conn = self._connect(url)

    @staticmethod
    def _connect(url: str):
        try:
            import psycopg                          # psycopg3
        except ImportError:
            try:
                import psycopg2 as psycopg          # fallback
            except ImportError:
                raise RuntimeError(
                    "Postgres driver chưa cài (pip install 'psycopg[binary]') — PR-003") from None
        return psycopg.connect(url)

    def _check_prov(self, table: str, row: Dict) -> None:
        if table not in CHAIN_TABLES:
            raise ValueError(f"table không hợp lệ: {table}")
        if table in PROV_TABLES:
            ds = row.get("data_state")
            if ds is None:
                raise ValueError(f"{table}: thiếu provenance.data_state (CTO rule)")
            if ds not in _LIVE_STATES:
                raise ValueError(
                    f"PostgresRepository từ chối data_state={ds} (chỉ LIVE/PRODUCTION_VERIFIED)")

    def insert(self, table: str, row: Dict) -> None:
        self._check_prov(table, row)
        cols = list(row.keys())
        ph = ",".join(["%s"] * len(cols))
        sql = f'INSERT INTO {table} ({",".join(cols)}) VALUES ({ph})'
        if "id" in cols:
            upd = [c for c in cols if c != "id"]
            sql += (f" ON CONFLICT (id) DO UPDATE SET " +
                    ", ".join(f"{c}=EXCLUDED.{c}" for c in upd)) if upd else " ON CONFLICT (id) DO NOTHING"
        cur = self.conn.cursor()
        cur.execute(sql, tuple(row.values()))
        self.conn.commit()

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def count(self, table: str) -> int:
        if table not in CHAIN_TABLES:
            raise ValueError(f"table không hợp lệ: {table}")
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]


def select_repository(env: Optional[Mapping[str, str]] = None):
    """Chọn adapter theo môi trường. LIVE → Postgres (gated); còn lại → Sqlite dry-run."""
    env = env or {}
    if env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL"):
        return PostgresRepository(env)      # sẽ raise tới khi driver+creds sẵn
    return SqliteRepository(data_state="DRY_RUN")
