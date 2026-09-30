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
from data_access import Repo as _SqliteRepo, CHAIN_TABLES   # noqa: E402


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
    """LIVE adapter (Supabase/Postgres). Gated: cần credential; chưa bật driver (PR-003)."""
    data_state_scope = {"LIVE", "PRODUCTION_VERIFIED"}

    def __init__(self, env: Optional[Mapping[str, str]] = None):
        env = env or {}
        url = env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")
        if not url:
            raise RuntimeError("PostgresRepository cần DATABASE_URL/SUPABASE_DB_URL (PR-003) — chưa cấp")
        # Driver mạng (psycopg) chưa bật trong repo — go-live sẽ nối. Không giả lập LIVE bằng SQLite.
        raise NotImplementedError("LIVE Postgres adapter chờ credential + driver (PR-003)")

    def insert(self, table: str, row: Dict) -> None:  # pragma: no cover
        raise NotImplementedError
    def query(self, sql: str, params: tuple = ()) -> List[Dict]:  # pragma: no cover
        raise NotImplementedError
    def count(self, table: str) -> int:  # pragma: no cover
        raise NotImplementedError


def select_repository(env: Optional[Mapping[str, str]] = None):
    """Chọn adapter theo môi trường. LIVE → Postgres (gated); còn lại → Sqlite dry-run."""
    env = env or {}
    if env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL"):
        return PostgresRepository(env)      # sẽ raise tới khi driver+creds sẵn
    return SqliteRepository(data_state="DRY_RUN")
