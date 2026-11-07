"""AFFOS Revenue Ingestion API (S2/S3 + v2 + S5A — additive, DRY-RUN by construction).

HTTP operations (wired into runtime/server.py):
  POST /affos/revenue/ingest           — trigger an affiliate ingestion run.
  POST /affos/revenue/approve          — grant a scoped, expiring live-ingest approval.
  POST /affos/revenue/approve/revoke   — revoke an approval (blocks live mode).
  GET  /affos/revenue/report           — read-only revenue/proof summary.

Invariants:
  - AuthZ reuses apps/auth-rbac JWT HS256 + RBAC. Hardened verification: signature, expiry, and —
    when configured via AFFOS_JWT_ISS / AFFOS_JWT_AUD — issuer and audience. `revenue:ingest` for
    ingest, `revenue:read` for report, `revenue:approve` for grant/revoke. Secret from env only.
  - NO `approved` in the request body. Live runs require a SERVER-SIDE, provider+environment scoped,
    time-windowed, expiring approval (granted via /approve). No active approval -> 424.
  - Two-layer idempotency: request Idempotency-Key (same body -> cached 200; different body -> 409);
    row-level dedupe is the DB's deterministic-id upsert + unique(source, source_record_id).
  - Durable persistence (approvals / idempotency / audit) via RevenueStore when a store is supplied;
    survives restart and is concurrency-safe. A process-local in-memory fallback is used only when no
    store is configured (pure dry-run without a DB).
  - Impact is OFF (CTO): provider "impact" -> 403. No auto-promotion.
  - Request size limit (413) and rate limit (429). Rate limiting here is PROCESS-LOCAL (per worker),
    NOT distributed; a multi-replica deployment needs a shared limiter (deferred — see design).
  - The ingest handler never supplies a production transport, so run_ingestion() only STOPs/dry-runs.
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
DISABLED_PROVIDERS = ("impact",)
VALID_MODES = ("dry-run", "live")

MAX_BODY_BYTES = 65536
RATE_LIMIT_PER_MIN = 30
RATE_WINDOW_S = 60

# Process-local fallbacks (used only when no durable store is configured).
_DEFAULT_IDEM_STORE: Dict[str, Dict] = {}
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


def _aud_ok(claim_aud, required: str) -> bool:
    if isinstance(claim_aud, (list, tuple)):
        return required in claim_aud
    return claim_aud == required


def _default_verify(token: str, secret: str, permission: str,
                    env: Optional[Mapping[str, str]] = None) -> Dict:
    """Hardened JWT verify (reuses auth-rbac jwt_util + RBAC matrix; no crypto fork).
    Checks signature + expiry (jwt_util), optional issuer/audience (when configured), then permission.
    Raises AuthFailure(401|403)."""
    env = env or {}
    if _AUTH_SRC not in sys.path:
        sys.path.insert(0, _AUTH_SRC)
    from auth import jwt_util  # noqa: E402
    from rbac import matrix  # noqa: E402

    if not token:
        raise AuthFailure(401, "missing token")
    try:
        claims = jwt_util.decode(token, secret)      # signature + exp
    except jwt_util.JWTError as e:
        raise AuthFailure(401, str(e)) from None

    iss = env.get("AFFOS_JWT_ISS")
    if iss and claims.get("iss") != iss:
        raise AuthFailure(401, "invalid issuer") from None
    aud = env.get("AFFOS_JWT_AUD")
    if aud and not _aud_ok(claims.get("aud"), aud):
        raise AuthFailure(401, "invalid audience") from None

    if not matrix.has_permission(claims.get("roles", []), permission):
        raise AuthFailure(403, f"missing permission: {permission}")
    return claims


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


def is_approved(provider: str, environment: str, now: datetime, approvals: List[Dict]) -> bool:
    """In-memory approval check (fallback when no durable store). Durable path uses RevenueStore."""
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
                 verify: Callable = _default_verify, store=None,
                 approvals: Optional[List] = None, audit_sink: Optional[List] = None,
                 now: Optional[datetime] = None) -> Tuple[int, Dict]:
    env = dict(env if env is not None else os.environ)
    approvals = _DEFAULT_APPROVALS if approvals is None else approvals
    audit_sink = _DEFAULT_AUDIT if audit_sink is None else audit_sink
    secret = env.get("AUTH_SECRET", "")
    now = now or datetime.now(timezone.utc)

    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        claims = verify(token, secret, REVENUE_APPROVE_PERMISSION, env)
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

    environment = str(data.get("environment") or _environment(env))
    actor = (claims or {}).get("sub")
    if store is not None:
        rec = store.add_approval(provider, environment, data["window_start"], data["window_end"],
                                 data["expires_at"], actor)
        store.audit("revenue_approval_grant", actor, provider,
                    {"environment": environment, "approval_id": rec["id"], "expires_at": rec["expires_at"]})
    else:
        rec = {"id": "appr_" + hashlib.sha1(
            f"{provider}:{data['window_start']}:{data['expires_at']}:{_now_iso()}".encode()).hexdigest()[:16],
            "provider": provider, "environment": environment,
            "window_start": str(data["window_start"]), "window_end": str(data["window_end"]),
            "expires_at": str(data["expires_at"]), "granted_by": actor,
            "granted_at": _now_iso(), "status": "active"}
        approvals.append(rec)
        audit_sink.append({"ts": _now_iso(), "event": "revenue_approval_grant", "actor": actor,
                           "target": provider, "meta": {"environment": environment, "approval_id": rec["id"]}})
    return 201, rec


def handle_revoke(raw_body: bytes, headers: Mapping[str, str],
                  env: Optional[Mapping[str, str]] = None, *,
                  verify: Callable = _default_verify, store=None,
                  approvals: Optional[List] = None) -> Tuple[int, Dict]:
    env = dict(env if env is not None else os.environ)
    approvals = _DEFAULT_APPROVALS if approvals is None else approvals
    secret = env.get("AUTH_SECRET", "")
    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        claims = verify(token, secret, REVENUE_APPROVE_PERMISSION, env)
    except AuthFailure as e:
        return e.code, {"error": e.message}
    try:
        data = json.loads(raw_body or b"{}")
        approval_id = str(data["approval_id"])
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        return 400, {"error": "approval_id required"}

    actor = (claims or {}).get("sub")
    if store is not None:
        ok = store.revoke_approval(approval_id, actor)
        if ok:
            store.audit("revenue_approval_revoke", actor, approval_id, {"approval_id": approval_id})
    else:
        ok = False
        for a in approvals:
            if a.get("id") == approval_id and a.get("status") == "active":
                a["status"] = "revoked"
                ok = True
    return (200, {"revoked": True, "approval_id": approval_id}) if ok else \
           (404, {"error": "no active approval with that id"})


def handle_ingest(raw_body: bytes, headers: Mapping[str, str],
                  env: Optional[Mapping[str, str]] = None, *,
                  verify: Callable = _default_verify, ingest: Callable = _default_ingest,
                  store=None, idem_store: Optional[Dict] = None, audit_sink: Optional[List] = None,
                  approvals: Optional[List] = None, rate_store: Optional[Dict] = None,
                  clock: Callable[[], float] = _mono, now: Optional[datetime] = None) -> Tuple[int, Dict]:
    env = dict(env if env is not None else os.environ)
    idem_store = _DEFAULT_IDEM_STORE if idem_store is None else idem_store
    audit_sink = _DEFAULT_AUDIT if audit_sink is None else audit_sink
    approvals = _DEFAULT_APPROVALS if approvals is None else approvals
    rate_store = _DEFAULT_RATE if rate_store is None else rate_store
    secret = env.get("AUTH_SECRET", "")
    now = now or datetime.now(timezone.utc)

    if raw_body is not None and len(raw_body) > MAX_BODY_BYTES:
        return 413, {"error": f"request body exceeds {MAX_BODY_BYTES} bytes"}

    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        claims = verify(token, secret, REVENUE_INGEST_PERMISSION, env)
    except AuthFailure as e:
        return e.code, {"error": e.message}

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

    # Idempotency (durable store if available; else in-memory).
    idem_key = headers.get("Idempotency-Key") or ""
    body_hash = hashlib.sha256(raw_body or b"").hexdigest()
    reserved = False
    if idem_key:
        if store is not None:
            state, cached = store.reserve(idem_key, body_hash)
            if state == "replay":
                return 200, cached
            if state == "conflict":
                return 409, {"error": "Idempotency-Key reused with a different body", "idempotency_key": idem_key}
            reserved = True
        else:
            prior = idem_store.get(idem_key)
            if prior is not None:
                if prior.get("body_hash") == body_hash:
                    return 200, prior["response"]
                return 409, {"error": "Idempotency-Key reused with a different body", "idempotency_key": idem_key}

    if _rate_limited((claims or {}).get("sub") or token, rate_store, clock):
        return 429, {"error": "rate limit exceeded", "retry_after_s": RATE_WINDOW_S}

    live = mode == "live"
    env_name = _environment(env)
    approved_live = (store.is_approved(provider, env_name, now) if store is not None
                     else is_approved(provider, env_name, now, approvals))
    if live and not approved_live:
        return 424, {"error": "no active approval for live ingestion (grant via /affos/revenue/approve)"}

    result = ingest(provider, env, start, end, live, None)
    response = {
        "status": "executed" if result.get("executed") else "stopped",
        "provider": provider, "mode": mode, "repository_mode": result.get("repository_mode"),
        "ingested": result.get("ingest", {}).get("ingested", 0) if result.get("executed") else 0,
        "real_commerce_proof": result.get("real_commerce_proof", "NOT YET VERIFIED"),
        "reason": result.get("reason", ""), "idempotency_key": idem_key or None,
    }

    meta = {"mode": mode, "window": {"start": start, "end": end},
            "ingested": response["ingested"], "status": response["status"]}
    actor = (claims or {}).get("sub")
    if store is not None:
        store.audit("revenue_ingest", actor, provider, meta)
        if reserved:
            store.commit_response(idem_key, response)
    else:
        audit_sink.append({"ts": _now_iso(), "event": "revenue_ingest", "actor": actor,
                           "target": provider, "meta": meta})
        if idem_key:
            idem_store[idem_key] = {"body_hash": body_hash, "response": response}
    return 200, response


def handle_report(query: Mapping[str, str], headers: Mapping[str, str],
                  env: Optional[Mapping[str, str]] = None, *,
                  verify: Callable = _default_verify) -> Tuple[int, Dict]:
    """Read-only revenue/proof summary. DRY-RUN returns a safe stub (no fabricated numbers);
    LIVE wires attribution.totals + proof against the real repository (never mutates records)."""
    env = dict(env if env is not None else os.environ)
    secret = env.get("AUTH_SECRET", "")
    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        verify(token, secret, REVENUE_READ_PERMISSION, env)
    except AuthFailure as e:
        return e.code, {"error": e.message}

    provider = str(query.get("provider", "")).lower()
    start = str(query.get("start", ""))
    end = str(query.get("end", ""))

    live = bool(env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL"))
    if not live:
        return 200, {"status": "ok", "repository_mode": "DRY-RUN", "provider": provider or None,
                     "window": {"start": start, "end": end}, "revenue": None,
                     "real_commerce_proof": "NOT YET VERIFIED",
                     "note": "dry-run: no live DB configured — reporting numbers unavailable"}
    core = os.path.abspath(os.path.join(_HERE, "..", "core"))
    attr = os.path.join(core, "attribution")
    for p in (core, attr):
        if p not in sys.path:
            sys.path.insert(0, p)
    import runtime as _rt  # noqa: E402
    import attribution  # noqa: E402
    import proof  # noqa: E402
    repo = _rt.build_repository(env)
    return 200, {"status": "ok", "repository_mode": "LIVE", "provider": provider or None,
                 "window": {"start": start, "end": end}, "totals": attribution.totals(repo),
                 "real_commerce_proof": proof.real_commerce_proof(repo)}


def handle_reconcile(query: Mapping[str, str], headers: Mapping[str, str],
                     env: Optional[Mapping[str, str]] = None, *,
                     verify: Callable = _default_verify) -> Tuple[int, Dict]:
    """Read-only reconciliation (S6). Requires `revenue:read`. DRY-RUN returns a stub (no DB);
    LIVE runs revenue_report.reconcile against the repository. Never mutates source records."""
    env = dict(env if env is not None else os.environ)
    secret = env.get("AUTH_SECRET", "")
    token = bearer_from_header(headers.get("Authorization", ""))
    try:
        verify(token, secret, REVENUE_READ_PERMISSION, env)
    except AuthFailure as e:
        return e.code, {"error": e.message}

    if not (env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")):
        return 200, {"status": "ok", "repository_mode": "DRY-RUN", "read_only": True,
                     "note": "dry-run: no live DB configured — reconciliation unavailable",
                     "alert": None}
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import runtime as _rt  # noqa: E402
    import revenue_report  # noqa: E402
    repo = _rt.build_repository(env)
    report = revenue_report.reconcile(repo, currency=query.get("currency"))
    report["repository_mode"] = "LIVE"
    return 200, report
