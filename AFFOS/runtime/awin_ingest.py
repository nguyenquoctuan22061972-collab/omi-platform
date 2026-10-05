"""AFFOS production AWIN ingestion caller (SPRINT 01 — prepared, NOT executed live).

This is the single production entrypoint that would wire AWIN transactions into the
LIVE Postgres repository. It is GATED and makes NO live call in this sprint:

  run_ingestion() refuses unless ALL hold:
    (a) approved=True (explicit CTO authorization),
    (b) repository_mode == LIVE (DATABASE_URL/SUPABASE_DB_URL configured),
    (c) a production transport (real egress) is supplied.
  Otherwise it STOPS and returns real_commerce_proof = NOT YET VERIFIED. Seed/test data
  is never substituted. No secret is read or printed.

Only when all three hold does it construct a PostgresRepository (via runtime.build_repository)
and call awin_live.AwinLiveClient.ingest_transactions — which itself guards against SQLite.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Mapping, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "connectors", "awin"))
import runtime  # noqa: E402


def _stop(reason: str, mode: str) -> Dict:
    return {"executed": False, "reason": reason, "repository_mode": mode,
            "awin_live": False, "real_commerce_proof": "NOT YET VERIFIED"}


def run_ingestion(env: Optional[Mapping[str, str]] = None, start: str = "", end: str = "",
                  approved: bool = False, transport=None) -> Dict:
    env = dict(env or {})
    mode = runtime.repository_mode(env)

    if not approved:
        return _stop("CTO approval required before any AWIN live ingestion — STOP.", mode)
    if mode != "LIVE":
        return _stop("repository is DRY-RUN; LIVE requires DATABASE_URL/SUPABASE_DB_URL.", mode)
    if transport is None or not getattr(transport, "is_production", False):
        return _stop("production transport (real egress) required; refusing fake/test transport.", mode)

    # --- reachable ONLY with approval + LIVE repo + production transport ---
    from awin_live import AwinLiveClient              # local import; no network at module load
    repo = runtime.build_repository(env)              # PostgresRepository (LIVE)
    client = AwinLiveClient(env, transport=transport)
    result = client.ingest_transactions(repo, start, end)   # real; guarded against SQLite
    return {"executed": True, "repository_mode": mode, "awin_live": True,
            "ingest": result, "real_commerce_proof": "NOT YET VERIFIED"}
    # NOTE: proof stays NOT YET VERIFIED until the full chain is independently verified.
