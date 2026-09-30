"""AFFOS — AWIN GATE 1 preflight (CTO GATE 1: REAL AWIN CONNECTION).

Purpose: PREPARE and SHOW the exact production-verification procedure with every
secret redacted, and verify credential presence WITHOUT printing any token value.

Hard rules enforced here:
  - Secrets are read from environment ONLY; their VALUES are never printed, logged,
    returned, or committed. Only presence/length is reported.
  - The first real production call is GATED: it runs only when (a) CTO approval is
    passed explicitly, (b) credentials are securely configured, and (c) a production
    transport (real egress) is supplied. Otherwise it STOPS and returns NOT YET VERIFIED.
  - Seed/test data is NEVER substituted for a production result.
No network happens on import or in dry-run.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Mapping, Optional

sys.path.insert(0, os.path.dirname(__file__))
from awin_live import AwinLiveClient, ProductionTransport, AWIN_BASE  # noqa: E402

REDACTED = "***REDACTED***"


def _present(env: Mapping[str, str], key: str) -> Dict:
    """Report ONLY presence + length. Never the value."""
    v = env.get(key)
    return {"key": key, "set": bool(v), "len": (len(v) if v else 0)}


def credential_status(env: Mapping[str, str]) -> Dict:
    tok = _present(env, "AWIN_API_TOKEN")
    pid = _present(env, "AWIN_PUBLISHER_ID")
    return {"AWIN_API_TOKEN": tok, "AWIN_PUBLISHER_ID": pid,
            "ready": tok["set"] and pid["set"]}


def redacted_procedure(env: Optional[Mapping[str, str]] = None) -> Dict:
    """The EXACT commands/requests that WILL run for the live check — secrets redacted."""
    pid = "<AWIN_PUBLISHER_ID>"   # rendered as placeholder; real id only injected at call time
    return {
        "step1_configure_secret":
            "Configure AWIN_API_TOKEN and AWIN_PUBLISHER_ID as ENVIRONMENT SECRETS "
            "(never in Git, CLI history, logs, or source).",
        "step2_auth_header": f"Authorization: Bearer {REDACTED}",
        "step3_offers_request":
            f"GET {AWIN_BASE}/publishers/{pid}/programmes/?relationship=joined",
        "step4_transactions_request":
            f"GET {AWIN_BASE}/publishers/{pid}/transactions/"
            f"?startDate=<YYYY-MM-DD>&endDate=<YYYY-MM-DD>&timezone=UTC",
        "step5_run":
            "python3 -c \"import os; from gate1_preflight import live_verify; "
            "from awin_live import ProductionTransport; "
            "print(live_verify(os.environ, approved=True, transport=ProductionTransport()))\"",
        "note": "Token is supplied only via env at call time; never echoed, logged, or committed.",
    }


def live_verify(env: Mapping[str, str], approved: bool = False,
                transport=None) -> Dict:
    """GATED real production verification. STOPS unless approval + creds + production transport.

    Returns NOT YET VERIFIED on any auth/permission/empty/failure. Never substitutes seed.
    """
    st = credential_status(env)
    base = {"authentication": "NOT VERIFIED", "api_connectivity": "NOT VERIFIED",
            "production_offer": "NOT VERIFIED", "production_transaction": "NOT VERIFIED",
            "production_commission": "NOT VERIFIED", "production_revenue": "NOT VERIFIED",
            "currency": "UNKNOWN", "provenance": "none (no production call)",
            "real_commerce_proof": "NOT YET VERIFIED", "executed": False}

    if not approved:
        base["reason"] = "CTO approval required before the first production call — STOP."
        return base
    if not st["ready"]:
        base["reason"] = "Credentials not securely configured (env secrets missing)."
        return base
    if transport is None or not getattr(transport, "is_production", False):
        base["reason"] = "Production transport (real egress) required; refusing fake/test transport."
        return base

    # --- Only reachable with approval + creds + production transport (real egress). ---
    client = AwinLiveClient(env, transport=transport)
    a = client.auth()
    if not a.get("ok"):
        base["reason"] = "auth blocked"
        return base
    base["authentication"] = "OK"
    try:
        offers = client.get_offers()            # real production call
    except Exception as e:                        # auth/permission/http/network/currency
        base["reason"] = f"{type(e).__name__}"    # never includes secret material
        return base
    base["api_connectivity"] = "OK"
    if not offers.get("ok") or offers.get("count", 0) == 0:
        base["reason"] = "no valid production offer"
        return base
    base["production_offer"] = f"{offers['count']} programme(s)"
    base["currency"] = offers["offers"][0].get("currency", "UNKNOWN")
    base["provenance"] = "source=awin_production, data_state=PRODUCTION_VERIFIED (from real API)"
    # Transactions/commissions/revenue require a Postgres/LIVE repository (CTO rule) and a
    # real transaction to exist — proof stays NOT YET VERIFIED until that chain is confirmed.
    base["executed"] = True
    base["reason"] = "offers retrieved; transaction/commission/revenue chain not yet confirmed"
    return base


def run(env: Optional[Mapping[str, str]] = None, approved: bool = False) -> Dict:
    env = dict(env or {})
    cred = credential_status(env)
    return {
        "credential_status": cred,
        "redacted_procedure": redacted_procedure(env),
        "egress_note": "external probe required — Awin host must be reachable from the runtime",
        "gate1": live_verify(env, approved=approved),
    }


if __name__ == "__main__":   # dry-run only; NEVER approved from the CLI default
    import json
    print(json.dumps(run(os.environ, approved=False), indent=2))
