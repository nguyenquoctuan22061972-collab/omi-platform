"""AFFOS.1 production Impact ingestion caller (GATE-2 — prepared, NOT executed live).

Mirrors runtime/awin_ingest.py. Single production entrypoint that would wire Impact Actions
into the LIVE Postgres repository. It is GATED and makes NO live call this gate:

  run_ingestion() refuses unless ALL hold:
    (a) approved=True (explicit CTO authorization),
    (b) repository_mode == LIVE (DATABASE_URL/SUPABASE_DB_URL configured),
    (c) a production transport (real egress) is supplied.
  Otherwise STOPS → real_commerce_proof = NOT YET VERIFIED. Seed/test data never substituted.

Even when all three hold and a real call is made, Impact records remain is_real()==False until
the CTO adds impact_production to provenance.PRODUCTION_SOURCES (not done this gate). No secret
is read or printed.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Mapping, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "connectors", "impact"))

# runtime/ is a namespace package, so a bare `import runtime` can bind the package DIRECTORY
# (no functions) when this module is imported as `runtime.impact_ingest`. Load runtime.py by
# its file path so repository_mode()/build_repository() are always available, in any context.
import importlib.util as _ilu  # noqa: E402
_rt_spec = _ilu.spec_from_file_location("affos_runtime_core", os.path.join(_HERE, "runtime.py"))
runtime = _ilu.module_from_spec(_rt_spec)
_rt_spec.loader.exec_module(runtime)  # noqa: E402


def _stop(reason: str, mode: str) -> Dict:
    return {"executed": False, "reason": reason, "repository_mode": mode,
            "impact_live": False, "provider": "impact",
            "real_commerce_proof": "NOT YET VERIFIED"}


def run_ingestion(env: Optional[Mapping[str, str]] = None, start: str = "", end: str = "",
                  approved: bool = False, transport=None) -> Dict:
    env = dict(env or {})
    mode = runtime.repository_mode(env)

    if not approved:
        return _stop("CTO approval required before any Impact live ingestion — STOP.", mode)
    if mode != "LIVE":
        return _stop("repository is DRY-RUN; LIVE requires DATABASE_URL/SUPABASE_DB_URL.", mode)
    if transport is None or not getattr(transport, "is_production", False):
        return _stop("production transport (real egress) required; refusing fake/test transport.", mode)

    # --- reachable ONLY with approval + LIVE repo + production transport ---
    from impact_live import ImpactLiveClient            # local import; no network at module load
    repo = runtime.build_repository(env)                # PostgresRepository (LIVE)
    client = ImpactLiveClient(env, transport=transport)
    result = client.ingest_actions(repo, start, end)    # real; guarded against SQLite
    return {"executed": True, "repository_mode": mode, "impact_live": True, "provider": "impact",
            "ingest": result, "real_commerce_proof": "NOT YET VERIFIED"}
    # NOTE: impact_production is not whitelisted in PRODUCTION_SOURCES, so these records are
    # non-real; proof stays NOT YET VERIFIED until the CTO approves that + independent verification.
