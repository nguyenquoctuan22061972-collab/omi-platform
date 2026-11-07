"""AFFOS Revenue Ingestion API (S2/S3 + Phase-3 v2 revision — additive, DRY-RUN by construction).

HTTP operations (wired into runtime/server.py):

  POST /affos/revenue/ingest    — trigger an affiliate ingestion run.
  POST /affos/revenue/approve   — grant a scoped, expiring live-ingest approval.
  GET  /affos/revenue/report    — read-only revenue/proof summary.

Phase-3 v2 design invariants (see design doc):
  1. NO `approved` in the request body. Live runs require a SERVER-SIDE approval record that is
     provider+environment scoped, time-windowed and expiring (granted via /approve with the
     `revenue:approve` permission). The ingest endpoint can never self-approve.
  2. Two-layer idempotency: request `Idempotency-Key` (replay SAME body -> cached 200; DIFFERENT
     body + same key -> 409). Row-level dedupe stays the DB's job (deterministic id upsert).
  3. AuthZ reuses apps/auth-rbac (JWT HS256 + RBAC). `revenue:ingest` for ingest, `revenue:read`
     for report, `revenue:approve` for grant. Secret from env AUTH_SECRET only (never logged).
  4. Impact is OFF (CTO): provider "impact" -> 403 until re-approved. No auto-promotion.
  5. Request size limit (413) and per-token rate limit (429 + Retry-After).

The ingest handler NEVER supplies a production transport, so run_ingestion() can only STOP/dry-run;
no live affiliate call is possible from this endpoint (a later sprint wires the transport).

Durable stores (approvals / idempotency / rate window) are process-local here — production persists
them in the DB (requires a migration, out of this code-only sprint). No secret is read or printed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Callable, Dict, List, Mapping, Optional, Tuple

_HERE = os.path.dirname(__file__)
_AUTH_SRC = os.path.abspath(os.path.join(_HERE, "..", "..", "apps", "auth-rbac", "src"))

REVENUE_INGEST_PERMISSION = "revenue:ingest"
REVENUE_READ_PERMISSION = "revenue:read"
REVENUE_APPROVE_PERMISSION = "revenue:approve"

RECOGNISED_PROVIDERS = ("awin", "impact")
DISABLED_PROVIDERS = ("impact",)                 # CTO: Impact OFF (no auto-promotion)
VALID_MODES = ("dry-run", "live")

MAX_BODY_BYTES = 65536                            # 64 KiB — ingest bodies are tiny
RATE_LIMIT_PER_MIN = 30
RATE_WINDOW_S = 60

# Process-local stores (production persists these in the DB).
_DEFAULT_IDEM_STORE: Dict[str, Dict] = {}        # key -> {"body_hash", "response"}
_DEFAULT_AUDIT: List[Dict] = []
_DEFAULT_APPROVALS: List[Dict] = []
_DEFAULT_RATE: Dict[str, List[float]] = {}


class AuthFailure(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mono() -> float:
    import time
    return time.monotonic()


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
    import impact_ingest  # noqa: E402  (unreached: impact disabled earlier)
    return impact_ingest.run_ingestion(env, start=start, end=end, approved=approved,
                                       transport=transport)


def _looks_iso8601(value: str) -> bool:
    v = (value or "").strip()
    if len(v) < 10:
        return False
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _environment(env: Mapping[str, str]) -> str:
    return env.get("AFFOS_ENVIRONMENT", "production")


def is_approved(provider: str, environment: str, now: datetime,
                approvals: List[Dict]) -> bool:
    """An active approval for (provider, environment) whose validity window contains `now` and
    whose expiry has not passed. Provider-scoped -> an AWIN approval never covers Impact."""
    for a in approvals:
        if a.get("status") != "active":
            continue
        if a.get("provider") != provider or a.get("environment") != environment:
            continue
        try:
            ws = datetime.fromisoformat(a["window_start"].replace("Z", "+00:00"))
            we = datetime.fromisoformat(a["window_end"].replace("Z", "+00:00"))
            exp = datetime.fromisoformat(a["expires_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if ws <= now <= we and now < exp:
            return True
    return False


def _rate_limited(subject: str, store: Dict[str, List[float]], clock: Callable[[], float]) -> bool:
    now = clock()
    hits = [t for t in store.get(subject, []) if now - t < RATE_WINDOW_S]
    if len(hits) >= RATE_LIMIT_PER_MIN:
        store[subject] = hits
        return True
    hits.append(now)
    store[subject] = hits
    return False


def handle_grant(raw_body: bytes, headers: Mapping[str, str],
                 env: Optional[Mapping[str, str]] = None, *,
                 verify: Callable = _default_verify,
                 approvals: Optional[List] = None,
                 audit_sink: Optional[List] = None,
                 now: Optional[datetime] = None) -> Tuple[int, Dict]:
    """Grant a scoped, expiring live-ingest approval. Requires `revenue:approve`. Audited.
    This is the ONLY way live ingestion becomes authorized; the ingest endpoint cannot self-approve."""
    env = dict(env if env is not None else os.environ)
    approvals = _DEFAULT_APPROVALS if approvals is None else approvals
    audit_sink = _DEFAULT_AUDIT if audit_sink is None else audit_sink
    secret = env.get("AUTH_SECRET", "")
    now = now or datetime.now(timezone.utc)

    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        claims = verify(token, secret, REVENUE_APPROVE_PERMISSION)
    except AuthFailure as e:
        return e.code, {"error": e.message}

    try:
        data = json.loads(raw_body or b"{}")
        if not isinstance(data, dict):
            raise ValueError("body must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        return 400, {"error": f"invalid JSON body: {e}"}

    provider = str(data.get("provider", "")).lower()
    if provider not in RECOGNISED_PROVIDERS:
        return 400, {"error": f"provider must be one of {list(RECOGNISED_PROVIDERS)}"}
    if provider in DISABLED_PROVIDERS:
        return 403, {"error": f"{provider} is disabled (CTO: Impact OFF) — cannot be approved"}
    for field in ("window_start", "window_end", "expires_at"):
        if not _looks_iso8601(str(data.get(field, ""))):
            return 400, {"error": f"{field} must be ISO-8601"}

    record = {
        "id": "appr_" + hashlib.sha1(
            f"{provider}:{data['window_start']}:{data['expires_at']}:{_now_iso()}".encode()
        ).hexdigest()[:16],
        "provider": provider,
        "environment": str(data.get("environment") or _environment(env)),
        "window_start": str(data["window_start"]),
        "window_end": str(data["window_end"]),
        "expires_at": str(data["expires_at"]),
        "granted_by": (claims or {}).get("sub"),
        "granted_at": _now_iso(),
        "status": "active",
    }
    approvals.append(record)
    audit_sink.append({"ts": _now_iso(), "event": "revenue_approval_grant",
                       "actor": record["granted_by"], "target": provider,
                       "meta": {"environment": record["environment"],
                                "window": {"start": record["window_start"], "end": record["window_end"]},
                                "expires_at": record["expires_at"], "approval_id": record["id"]}})
    return 201, record


def handle_ingest(raw_body: bytes, headers: Mapping[str, str],
                  env: Optional[Mapping[str, str]] = None, *,
                  verify: Callable = _default_verify,
                  ingest: Callable = _default_ingest,
                  idem_store: Optional[Dict] = None,
                  audit_sink: Optional[List] = None,
                  approvals: Optional[List] = None,
                  rate_store: Optional[Dict] = None,
                  clock: Callable[[], float] = _mono,
                  now: Optional[datetime] = None) -> Tuple[int, Dict]:
    env = dict(env if env is not None else os.environ)
    idem_store = _DEFAULT_IDEM_STORE if idem_store is None else idem_store
    audit_sink = _DEFAULT_AUDIT if audit_sink is None else audit_sink
    approvals = _DEFAULT_APPROVALS if approvals is None else approvals
    rate_store = _DEFAULT_RATE if rate_store is None else rate_store
    secret = env.get("AUTH_SECRET", "")
    now = now or datetime.now(timezone.utc)

    # 0. Request size limit (cheap, before any work).
    if raw_body is not None and len(raw_body) > MAX_BODY_BYTES:
        return 413, {"error": f"request body exceeds {MAX_BODY_BYTES} bytes"}

    # 1. AuthN/AuthZ (reuse auth-rbac). Never echoes the token.
    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        claims = verify(token, secret, REVENUE_INGEST_PERMISSION)
    except AuthFailure as e:
        return e.code, {"error": e.message}

    # 2. Parse + validate body (NO `approved` field — that is server-side now).
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

    if provider not in RECOGNISED_PROVIDERS:
        return 400, {"error": f"provider must be one of {list(RECOGNISED_PROVIDERS)}"}
    if provider in DISABLED_PROVIDERS:
        return 403, {"error": f"{provider} ingestion disabled (CTO: Impact OFF)"}
    if mode not in VALID_MODES:
        return 400, {"error": f"mode must be one of {list(VALID_MODES)}"}
    if not (_looks_iso8601(start) and _looks_iso8601(end)):
        return 400, {"error": "window.start and window.end must be ISO-8601"}

    # 3. Idempotency (request-level): same key + same body -> cached 200; different body -> 409.
    idem_key = headers.get("Idempotency-Key") or ""
    body_hash = hashlib.sha256(raw_body or b"").hexdigest()
    if idem_key and idem_key in idem_store:
        prior = idem_store[idem_key]
        if prior.get("body_hash") == body_hash:
            return 200, prior["response"]
        return 409, {"error": "Idempotency-Key reused with a different body", "idempotency_key": idem_key}

    # 4. Per-token rate limit.
    if _rate_limited((claims or {}).get("sub") or token, rate_store, clock):
        return 429, {"error": "rate limit exceeded", "retry_after_s": RATE_WINDOW_S}

    # 5. Server-side approval gate for live runs (replaces the old body `approved` flag).
    live = mode == "live"
    if live and not is_approved(provider, _environment(env), now, approvals):
        return 424, {"error": "no active approval for live ingestion (grant via /affos/revenue/approve)"}

    # 6. Run. transport=None by construction -> run_ingestion() STOPs; dry-run otherwise.
    result = ingest(provider, env, start, end, live, None)

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

    # 7. Audit (never logs secrets).
    audit_sink.append({
        "ts": _now_iso(), "event": "revenue_ingest", "actor": (claims or {}).get("sub"),
        "target": provider, "meta": {"mode": mode, "window": {"start": start, "end": end},
                                     "ingested": response["ingested"], "status": response["status"]},
    })
    if idem_key:
        idem_store[idem_key] = {"body_hash": body_hash, "response": response}
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
