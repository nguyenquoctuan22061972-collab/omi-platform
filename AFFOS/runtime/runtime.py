"""AFFOS production runtime core (SPRINT 01 — additive, minimal).

Responsibilities:
  - repository_mode(env): report intended repo mode by ENV inspection only (no connect, no secret).
  - build_repository(env): construct the real adapter via core.repository.select_repository
    (DATABASE_URL/SUPABASE_DB_URL -> PostgresRepository; else SQLite DRY-RUN). Used by run paths,
    NOT by health.
  - health(env): a secret-free status dict (repository mode, driver availability, awin flag).

No secrets are read or printed (only presence of DB URL is reflected as a mode label).
Keeps existing DRY-RUN behavior intact; does NOT call AWIN live.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Mapping, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "core"))
import repository as _repository  # noqa: E402

VERSION = "runtime-sprint-01"


def repository_mode(env: Optional[Mapping[str, str]] = None) -> str:
    """LIVE iff a production DB URL is configured; else DRY-RUN. ENV inspection only."""
    env = env or {}
    return "LIVE" if (env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")) else "DRY-RUN"


def postgres_driver_available() -> bool:
    return bool(importlib.util.find_spec("psycopg") or importlib.util.find_spec("psycopg2"))


def build_repository(env: Optional[Mapping[str, str]] = None):
    """Construct the correct adapter (may connect). DRY-RUN -> SQLite; LIVE -> Postgres."""
    return _repository.select_repository(dict(env or {}))


def health(env: Optional[Mapping[str, str]] = None) -> Dict:
    """Secret-free runtime health. Never includes credential values."""
    env = env or {}
    return {
        "status": "ok",
        "service": "affos-runtime",
        "version": VERSION,
        "repository_mode": repository_mode(env),        # DRY-RUN | LIVE
        "postgres_driver": postgres_driver_available(),
        "awin_live_enabled": False,                      # LIVE AWIN not wired this sprint
        "ts": datetime.now(timezone.utc).isoformat(),
    }
