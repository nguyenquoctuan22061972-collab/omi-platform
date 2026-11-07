"""AFFOS Revenue Ingestion API (SPRINT S2/S3 — additive, DRY-RUN by construction).

Exposes two HTTP operations (wired into runtime/server.py):

  POST /affos/revenue/ingest   — trigger an affiliate ingestion run.
  GET  /affos/revenue/report   — read-only revenue/proof summary.

Design invariants (reuse > additive > no-fork):
  - AuthZ reuses apps/auth-rbac (JWT HS256 + RBAC matrix). Permission `revenue:ingest`
    for POST, `revenue:read` for GET. Secret from env AUTH_SECRET only (never logged).
  - The ingest handler NEVER supplies a production transport, so run_ingestion() can only
    STOP/dry-run — it cannot make a live affiliate call from this endpoint (that is a later
    sprint). No secret is read or printed.
  - Impact is OFF (CTO): provider "impact" is recognised but rejected 403 until re-approved.
  - Idempotency: an `Idempotency-Key` request header dedupes retried calls (replay -> 409).
    Row-level dedupe is the DB's job (source_record_id upsert), unchanged here.
  - Audit: every attempt appends an audit record (event=revenue_ingest).

Pure stdlib. Handlers are socket-free and unit-testable: they take raw body + a headers
mapping and return (status_code, dict).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Callable, Dict, List, Mapping, Optional, Tuple

_HERE = os.path.dirname(__file__)
_AUTH_SRC = os.path.abspath(os.path.join(_HERE, "..", "..", "apps", "auth-rbac", "src"))

REVENUE_INGEST_PERMISSION = "revenue:ingest"
REVENUE_READ_PERMISSION = "revenue:read"

# Providers recognised by validation; "impact" is recognised-but-disabled (CTO: Impact OFF).
RECOGNISED_PROVIDERS = ("awin", "impact")
DISABLED_PROVIDERS = ("impact",)
VALID_MODES = ("dry-run", "live")

# Process-local defaults (fine for S1–S4 dry-run; production would persist these in the DB).
_DEFAULT_IDEM_STORE: Dict[str, Dict] = {}
_DEFAULT_AUDIT: List[Dict] = []


class AuthFailure(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bearer_from_header(authorization: str) -> str:
    parts = (authorization or "").split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def _default_verify(token: str, secret: str, permission: str) -> Dict:
    """Reuse apps/auth-rbac RBAC middleware. Raises AuthFailure(401|403)."""
    if _AUTH_SRC not in sys.path:
        sys.path.insert(0, _AUTH_SRC)
    from rbac import middleware as mw  # noqa: E402  (reused module, not forked)

    try:
        return mw.require_permission(token, secret, permission)
    except mw.Unauthorized as e:
        raise AuthFailure(401, str(e)) from None
    except mw.Forbidden as e:
        raise AuthFailure(403, str(e)) from None


def _default_ingest(provider: str, env: Mapping[str, str], start: str, end: str,
                    approved: bool, transport) -> Dict:
    """Dispatch to the existing gated ingestion entrypoints. transport is always None here,
    so run_ingestion() can only STOP/dry-run — never a live call from this endpoint."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    if provider == "awin":
        import awin_ingest  # noqa: E402  (reused entrypoint)
        return awin_ingest.run_ingestion(env, start=start, end=end, approved=approved,
                                         transport=transport)
    # provider == "impact" never reaches here (disabled earlier); kept for completeness.
    import impact_ingest  # noqa: E402
    return impact_ingest.run_ingestion(env, start=start, end=end, approved=approved,
                                       transport=transport)


def _looks_iso8601(value: str) -> bool:
    """Lightweight ISO-8601 date/datetime check (no timezone math, no network)."""
    v = (value or "").strip()
    if len(v) < 10:
        return False
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def handle_ingest(raw_body: bytes, headers: Mapping[str, str],
                  env: Optional[Mapping[str, str]] = None, *,
                  verify: Callable = _default_verify,
                  ingest: Callable = _default_ingest,
                  idem_store: Optional[Dict] = None,
                  audit_sink: Optional[List] = None) -> Tuple[int, Dict]:
    env = dict(env if env is not None else os.environ)
    idem_store = _DEFAULT_IDEM_STORE if idem_store is None else idem_store
    audit_sink = _DEFAULT_AUDIT if audit_sink is None else audit_sink
    secret = env.get("AUTH_SECRET", "")

    # 1. AuthN/AuthZ (reuse auth-rbac). Never echoes the token.
    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        claims = verify(token, secret, REVENUE_INGEST_PERMISSION)
    except AuthFailure as e:
        return e.code, {"error": e.message}

    # 2. Parse + validate body.
    try:
        data = json.loads(raw_body or b"{}")
        if not isinstance(data, dict):
            raise ValueError("body must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        return 400, {"error": f"invalid JSON body: {e}"}

    provider = str(data.get("provider", "")).lower()
    mode = str(data.get("mode", "dry-run")).lower()
    window = data.get("window") or {}
    start = str(window.get("start", ""))
    end = str(window.get("end", ""))
    approved = bool(data.get("approved", False))

    if provider not in RECOGNISED_PROVIDERS:
        return 400, {"error": f"provider must be one of {list(RECOGNISED_PROVIDERS)}"}
    if provider in DISABLED_PROVIDERS:
        return 403, {"error": f"{provider} ingestion disabled (CTO: Impact OFF)"}
    if mode not in VALID_MODES:
        return 400, {"error": f"mode must be one of {list(VALID_MODES)}"}
    if not (_looks_iso8601(start) and _looks_iso8601(end)):
        return 400, {"error": "window.start and window.end must be ISO-8601"}
    if mode == "live" and not approved:
        return 424, {"error": "live ingestion requires approved=true (CTO authorization)"}

    # 3. Idempotency (request-level). Row-level dedupe stays in the DB adapter.
    idem_key = headers.get("Idempotency-Key") or ""
    if idem_key and idem_key in idem_store:
        return 409, {"error": "duplicate Idempotency-Key", "idempotency_key": idem_key}

    # 4. Run. transport=None by construction -> run_ingestion() STOPs for live; dry-run otherwise.
    result = ingest(provider, env, start, end, approved and mode == "live", None)

    response = {
        "status": "executed" if result.get("executed") else "stopped",
        "provider": provider,
        "mode": mode,
        "repository_mode": result.get("repository_mode"),
        "ingested": result.get("ingest", {}).get("ingested", 0) if result.get("executed") else 0,
        "real_commerce_proof": result.get("real_commerce_proof", "NOT YET VERIFIED"),
        "reason": result.get("reason", ""),
        "idempotency_key": idem_key or None,
    }

    # 5. Audit (never logs secrets).
    audit_sink.append({
        "ts": _now(), "event": "revenue_ingest", "actor": (claims or {}).get("sub"),
        "target": provider, "meta": {"mode": mode, "window": {"start": start, "end": end},
                                     "ingested": response["ingested"],
                                     "status": response["status"]},
    })
    if idem_key:
        idem_store[idem_key] = response
    return 200, response


def handle_report(query: Mapping[str, str], headers: Mapping[str, str],
                  env: Optional[Mapping[str, str]] = None, *,
                  verify: Callable = _default_verify) -> Tuple[int, Dict]:
    """Read-only revenue/proof summary. DRY-RUN returns a safe stub (no fabricated numbers);
    LIVE wires attribution.totals + proof against the real repository (later sprint supplies DB)."""
    env = dict(env if env is not None else os.environ)
    secret = env.get("AUTH_SECRET", "")
    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        verify(token, secret, REVENUE_READ_PERMISSION)
    except AuthFailure as e:
        return e.code, {"error": e.message}

    provider = str(query.get("provider", "")).lower()
    start = str(query.get("start", ""))
    end = str(query.get("end", ""))

    live = bool(env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL"))
    if not live:
        return 200, {
            "status": "ok", "repository_mode": "DRY-RUN",
            "provider": provider or None, "window": {"start": start, "end": end},
            "revenue": None, "real_commerce_proof": "NOT YET VERIFIED",
            "note": "dry-run: no live DB configured — reporting numbers unavailable",
        }
    # LIVE branch (not exercised in S1–S4 tests; no DB here). Lazy import to avoid DB deps in dry-run.
    core = os.path.abspath(os.path.join(_HERE, "..", "core"))
    attr = os.path.join(core, "attribution")
    for p in (core, attr):
        if p not in sys.path:
            sys.path.insert(0, p)
    import runtime as _rt  # noqa: E402
    import attribution  # noqa: E402
    import proof  # noqa: E402
    repo = _rt.build_repository(env)
    return 200, {
        "status": "ok", "repository_mode": "LIVE",
        "provider": provider or None, "window": {"start": start, "end": end},
        "totals": attribution.totals(repo),
        "real_commerce_proof": proof.real_commerce_proof(repo),
    }
