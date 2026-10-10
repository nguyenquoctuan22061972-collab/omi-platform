"""AFFOS Production Preflight — REAL-COMMERCE GATE #1 (FAST-TRACK).

Reports 8 gates and an overall readiness. Runnable in the Builder env (build/test)
or on the Production VPS (live commerce). It NEVER prints secrets (PRESENT/MISSING
only) and NEVER makes an authenticated AWIN commerce call — the real call stays the
separately-approved gate1_preflight.live_verify(approved=True) step, run only after
every required gate here PASSES.

Gates:
  1 AWIN credentials      PRESENT/MISSING
  2 AWIN API reachability PASS/FAIL   (unauthenticated connectivity probe only)
  3 Postgres connectivity PASS/FAIL
  4 Postgres write        PASS/FAIL   (temp table insert + ROLLBACK; touches no real table)
  5 Connector Interface   PASS/FAIL
  6 AWIN adapter          PASS/FAIL
  7 Secret scan           PASS/FAIL
  8 Tests                 PASS/FAIL
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Dict, Mapping, Optional

_HERE = os.path.dirname(__file__)
_AFFOS = os.path.abspath(os.path.join(_HERE, ".."))
for p in (os.path.join(_AFFOS, "core"),
          os.path.join(_AFFOS, "connectors"),
          os.path.join(_AFFOS, "connectors", "awin")):
    if p not in sys.path:
        sys.path.insert(0, p)

PRESENT, MISSING, PASS, FAIL = "PRESENT", "MISSING", "PASS", "FAIL"
_SECRET_PATS = [
    r"xox[bap]-[0-9A-Za-z-]{10,}", r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9._-]{12,}['\"]",
]


def gate_credentials(env: Mapping[str, str]) -> Dict:
    tok = bool(env.get("AWIN_API_TOKEN"))
    pid = bool(env.get("AWIN_PUBLISHER_ID"))
    return {"gate": "AWIN credentials", "status": PRESENT if (tok and pid) else MISSING,
            "detail": f"token={'set' if tok else 'missing'}, publisher_id={'set' if pid else 'missing'}"}


def gate_awin_reachable(timeout: int = 10) -> Dict:
    """Unauthenticated HTTPS connectivity probe to api.awin.com. No token sent."""
    import urllib.error
    import urllib.request
    from awin_live import AWIN_BASE
    try:
        req = urllib.request.Request(AWIN_BASE + "/", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.getcode()
        return {"gate": "AWIN API reachability", "status": PASS, "detail": f"HTTP {code}"}
    except urllib.error.HTTPError as e:
        # A reachable host that returns 401/403/404 at root still proves connectivity.
        ok = e.code in (401, 403, 404, 405)
        return {"gate": "AWIN API reachability", "status": PASS if ok else FAIL,
                "detail": f"HTTP {e.code} (host reachable)" if ok else f"HTTP {e.code}"}
    except Exception as e:
        return {"gate": "AWIN API reachability", "status": FAIL, "detail": f"{type(e).__name__}"}


def _pg_conn(env: Mapping[str, str]):
    from repository import PostgresRepository
    url = env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")
    if not url:
        return None, "DATABASE_URL/SUPABASE_DB_URL missing"
    return PostgresRepository._connect(url), ""


def gate_pg_connect(env: Mapping[str, str]) -> Dict:
    try:
        conn, why = _pg_conn(env)
        if conn is None:
            return {"gate": "Postgres connectivity", "status": FAIL, "detail": why}
        cur = conn.cursor(); cur.execute("SELECT 1"); cur.fetchone()
        try: conn.close()
        except Exception: pass
        return {"gate": "Postgres connectivity", "status": PASS, "detail": "SELECT 1 ok"}
    except Exception as e:
        return {"gate": "Postgres connectivity", "status": FAIL, "detail": f"{type(e).__name__}"}


def gate_pg_write(env: Mapping[str, str], _conn=None) -> Dict:
    """Prove write capability AND verified rollback, touching no business table / schema.

    In an explicit transaction: CREATE TEMP TABLE + INSERT, confirm the row is visible
    in-transaction, then ROLLBACK and VERIFY the rollback discarded it (the temp table no
    longer exists). PASS only if the row was written AND the rollback is confirmed. A rollback
    that errors or fails to discard → FAIL (never silently reported as rolled back).
    """
    conn = _conn
    try:
        if conn is None:
            conn, why = _pg_conn(env)
            if conn is None:
                return {"gate": "Postgres write", "status": FAIL, "detail": why}
        try:
            if hasattr(conn, "autocommit"):
                conn.autocommit = False     # a committed write cannot be rolled back — force a txn
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute("CREATE TEMP TABLE _affos_pf (x int)")
        cur.execute("INSERT INTO _affos_pf VALUES (1)")
        cur.execute("SELECT count(*) FROM _affos_pf")
        in_txn = cur.fetchone()[0]          # expect 1 inside the transaction
        conn.rollback()                      # NOT swallowed — a rollback error fails the gate
        # verify rollback actually discarded the temp table (DDL is transactional in Postgres)
        rolled_back = False
        try:
            c2 = conn.cursor()
            c2.execute("SELECT count(*) FROM _affos_pf")
            c2.fetchone()                    # table still visible → rollback NOT verified
        except Exception:
            try: conn.rollback()             # clear aborted-txn state
            except Exception: pass
            rolled_back = True               # table gone → rollback verified
        try: conn.close()
        except Exception: pass
        if in_txn == 1 and rolled_back:
            return {"gate": "Postgres write", "status": PASS,
                    "detail": "temp insert visible in-txn (1 row); rollback verified (temp table gone)"}
        return {"gate": "Postgres write", "status": FAIL,
                "detail": f"rollback not verified (in_txn={in_txn}, discarded={rolled_back})"}
    except Exception as e:
        return {"gate": "Postgres write", "status": FAIL, "detail": f"{type(e).__name__}"}


def gate_connector_interface() -> Dict:
    try:
        from connector_interface import verify_contract
        from adapters import AffiliateNetworkAdapter
        chk = verify_contract(AffiliateNetworkAdapter({}))
        return {"gate": "Connector Interface", "status": PASS if chk["contract_ok"] else FAIL,
                "detail": f"missing={chk['missing_capabilities']}"}
    except Exception as e:
        return {"gate": "Connector Interface", "status": FAIL, "detail": f"{type(e).__name__}"}


def gate_awin_adapter(env: Mapping[str, str]) -> Dict:
    try:
        from connector_interface import verify_contract
        from adapters import AwinAdapter
        a = AwinAdapter(env)
        chk = verify_contract(a)
        return {"gate": "AWIN adapter", "status": PASS if chk["contract_ok"] else FAIL,
                "detail": f"mode={a.mode()}, missing={chk['missing_capabilities']}"}
    except Exception as e:
        return {"gate": "AWIN adapter", "status": FAIL, "detail": f"{type(e).__name__}"}


def gate_secret_scan() -> Dict:
    hits = 0
    for root, _, files in os.walk(_AFFOS):
        if "__pycache__" in root or "/.git" in root:
            continue
        for fn in files:
            if not fn.endswith((".py", ".md", ".json", ".sql", ".sh")):
                continue
            try:
                with open(os.path.join(root, fn), encoding="utf-8", errors="ignore") as f:
                    t = f.read()   # context-managed so the file is always closed, even on error
            except Exception:
                continue
            for p in _SECRET_PATS:
                hits += len(re.findall(p, t))
    return {"gate": "Secret scan", "status": PASS if hits == 0 else FAIL, "detail": f"{hits} hit(s)"}


def gate_tests(run: bool = True) -> Dict:
    if not run:
        return {"gate": "Tests", "status": "SKIPPED", "detail": "run=False"}
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                           cwd=_AFFOS, capture_output=True, text=True, timeout=300)
        ok = r.returncode == 0
        tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
        return {"gate": "Tests", "status": PASS if ok else FAIL, "detail": tail[0]}
    except Exception as e:
        return {"gate": "Tests", "status": FAIL, "detail": f"{type(e).__name__}"}


# Gates that MUST pass before the real AWIN commerce call is permitted.
_REQUIRED = {"AWIN credentials": PRESENT, "AWIN API reachability": PASS,
             "Postgres connectivity": PASS, "Postgres write": PASS,
             "Connector Interface": PASS, "AWIN adapter": PASS,
             "Secret scan": PASS, "Tests": PASS}


def run(env: Optional[Mapping[str, str]] = None, run_tests: bool = True,
        probe_network: bool = True) -> Dict:
    env = dict(env or {})
    gates = [
        gate_credentials(env),
        gate_awin_reachable() if probe_network else {"gate": "AWIN API reachability", "status": "SKIPPED", "detail": "probe disabled"},
        gate_pg_connect(env),
        gate_pg_write(env),
        gate_connector_interface(),
        gate_awin_adapter(env),
        gate_secret_scan(),
        gate_tests(run=run_tests),
    ]
    ready = all(g["status"] == _REQUIRED.get(g["gate"]) for g in gates)
    return {"gates": gates, "ready_for_live_call": ready,
            "note": "real AWIN commerce call permitted ONLY when ready_for_live_call is True; "
                    "it is NOT made by this preflight."}


# ------------------------- AFFOS.1 Impact gates (additive) -------------------------
IMPACT_BASE = "https://api.impact.com"


def gate_impact_credentials(env: Mapping[str, str]) -> Dict:
    sid = bool(env.get("IMPACT_ACCOUNT_SID"))
    tok = bool(env.get("IMPACT_AUTH_TOKEN"))
    return {"gate": "Impact credentials", "status": PRESENT if (sid and tok) else MISSING,
            "detail": f"account_sid={'set' if sid else 'missing'}, auth_token={'set' if tok else 'missing'}"}


def gate_impact_reachable(timeout: int = 10) -> Dict:
    import urllib.error
    import urllib.request
    try:
        req = urllib.request.Request(IMPACT_BASE + "/", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"gate": "Impact API reachability", "status": PASS, "detail": f"HTTP {r.getcode()}"}
    except urllib.error.HTTPError as e:
        ok = e.code in (401, 403, 404, 405)
        return {"gate": "Impact API reachability", "status": PASS if ok else FAIL,
                "detail": f"HTTP {e.code} (host reachable)" if ok else f"HTTP {e.code}"}
    except Exception as e:
        return {"gate": "Impact API reachability", "status": FAIL, "detail": f"{type(e).__name__}"}


def gate_impact_adapter(env: Mapping[str, str]) -> Dict:
    try:
        from connector_interface import verify_contract
        from adapters import ImpactAdapter
        a = ImpactAdapter(env)
        chk = verify_contract(a)
        return {"gate": "Impact adapter", "status": PASS if chk["contract_ok"] else FAIL,
                "detail": f"mode={a.mode()}, missing={chk['missing_capabilities']}"}
    except Exception as e:
        return {"gate": "Impact adapter", "status": FAIL, "detail": f"{type(e).__name__}"}


def gate_impact_whitelist() -> Dict:
    """Reports whether impact_production is whitelisted for REAL (must stay NOT this gate)."""
    try:
        import provenance
        on = "impact_production" in provenance.PRODUCTION_SOURCES
        return {"gate": "Impact production whitelist", "status": "ENABLED" if on else "NOT_YET",
                "detail": "impact_production in PRODUCTION_SOURCES" if on else "withheld pending CTO approval"}
    except Exception as e:
        return {"gate": "Impact production whitelist", "status": FAIL, "detail": f"{type(e).__name__}"}


_IMPACT_REQUIRED = {"Impact credentials": PRESENT, "Impact API reachability": PASS,
                    "Postgres connectivity": PASS, "Postgres write": PASS,
                    "Impact adapter": PASS, "Secret scan": PASS, "Tests": PASS}


def run_impact(env: Optional[Mapping[str, str]] = None, run_tests: bool = True,
               probe_network: bool = True) -> Dict:
    """AFFOS.1 Impact-specific preflight (isolated from AWIN run())."""
    env = dict(env or {})
    gates = [
        gate_impact_credentials(env),
        gate_impact_reachable() if probe_network else {"gate": "Impact API reachability", "status": "SKIPPED", "detail": "probe disabled"},
        gate_pg_connect(env),
        gate_pg_write(env),
        gate_impact_adapter(env),
        gate_secret_scan(),
        gate_tests(run=run_tests),
        gate_impact_whitelist(),
    ]
    ready = all(g["status"] == _IMPACT_REQUIRED.get(g["gate"]) for g in gates if g["gate"] in _IMPACT_REQUIRED)
    whitelisted = any(g["gate"] == "Impact production whitelist" and g["status"] == "ENABLED" for g in gates)
    return {"gates": gates, "ready_for_impact_live_call": ready and whitelisted,
            "gates_ready_excluding_whitelist": ready,
            "note": "Impact live ingestion permitted ONLY when ready_for_impact_live_call is True "
                    "(all gates PASS AND impact_production whitelisted). This preflight makes no call."}


if __name__ == "__main__":
    import json
    which = "impact" if "--impact" in sys.argv else "awin"
    out = (run_impact if which == "impact" else run)(os.environ, run_tests=("--no-tests" not in sys.argv))
    for g in out["gates"]:
        print(f"{g['status']:>9}  {g['gate']:<28} {g['detail']}")
    key = "ready_for_impact_live_call" if which == "impact" else "ready_for_live_call"
    print(f"\n{'READY FOR IMPACT LIVE CALL' if which=='impact' else 'READY FOR LIVE CALL'}: {out[key]}")
