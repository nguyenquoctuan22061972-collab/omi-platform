"""AFFOS Token/Cost Ledger — Phase 0 (additive, measurement-only).

Purpose: capture a per-call cost/token record so a baseline cost/video and cost/workflow can be measured
BEFORE any optimization. Phase 0 is measurement ONLY — it does not change any pipeline behavior.

Design (approved Phase-0 spec + CODE-1):
  * NO new database and NO new table — rows are written to the EXISTING `audit_logs` table
    (id, event, actor, target, meta jsonb, ts), reusing the exact path RevenueStore.audit() uses.
    `event='cost.call'` for a metered call; `event='cost.confirm'` for a later billed-cost confirmation.
  * NO new privilege — the least-privilege runtime role has INSERT (only) on audit_logs (migration 0005;
    proven under RLS as affos_service). Both events are INSERTs, so the existing INSERT policy covers them.
    This module never UPDATEs or DELETEs (affos_service cannot), so state changes are append-only rows.
  * One code path for SQLite (tests/dry-run) and Postgres: only the placeholder ("?" vs "%s") and the
    jsonb cast differ, exactly like RevenueStore.

Idempotency (CODE-1, Option A = application-level, best-effort — documented concurrent-retry limits):
  * call_id       — one physical call attempt (unique; auto-generated if not supplied). Dedup unit for cost.
  * run_id        — one baseline run (one of the 5). Set by the orchestrator.
  * idempotency_key — stable logical identity across retries (default f"{run_id}:{step}:{video_id}").
  * attempt/status — retry chain; status in {pending, success, failed}. Append-only; read-time keeps the
    terminal row per call_id, so a pending+terminal pair or a double-logged attempt is counted ONCE.
  * Estimated vs billed — estimated_usd is computed/supplied now; the real billed amount arrives later as a
    SEPARATE `cost.confirm` row (no UPDATE). Read-time, a call's cost = confirmed_billed_usd if present else
    estimated_usd; reports split confirmed vs estimated so an estimate is never passed off as billed.

Honesty rule: if a call has no price basis, estimated_usd stays None (never fabricated); aggregations sum
only priced calls and report usd_unpriced_calls separately. No secret is read or printed.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

COST_EVENT = "cost.call"
CONFIRM_EVENT = "cost.confirm"
_TERMINAL = ("success", "failed")

# SQLite/dry-run convenience schema (prod reuses the existing 0001 audit_logs table — do NOT recreate it there).
AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  event TEXT NOT NULL,
  actor TEXT,
  target TEXT,
  meta TEXT,
  ts TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _estimated(r: Dict) -> Optional[float]:
    """estimated_usd with back-compat fallback to the legacy `usd` field."""
    v = r.get("estimated_usd", r.get("usd"))
    return None if v is None else float(v)


def _effective(r: Dict) -> Optional[float]:
    """A row's effective cost: confirmed billed if known, else estimated, else None (unpriced)."""
    cb = r.get("confirmed_billed_usd")
    return float(cb) if cb is not None else _estimated(r)


def _parse_ts(ts) -> Optional[datetime]:
    """audit_logs.ts as an aware datetime. PG returns a datetime; SQLite returns an ISO-8601 string.
    A naive value is assumed UTC. Unparseable -> None (age simply unknown, never fabricated)."""
    if ts is None:
        return None
    dt = ts if isinstance(ts, datetime) else None
    if dt is None:
        try:
            dt = datetime.fromisoformat(str(ts))
        except (ValueError, TypeError):
            return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class CostLedger:
    """Append-only cost/token ledger over the existing `audit_logs` table.

    `conn` is a DB-API connection (sqlite3 in tests; psycopg in prod). `placeholder` is "?" for SQLite,
    "%s" for Postgres. Writes use the same audit_logs shape as RevenueStore.audit()."""

    def __init__(self, conn, placeholder: str = "?"):
        self.conn = conn
        self.ph = placeholder
        # audit_logs.meta is jsonb on Postgres: a json-string param needs an explicit ::jsonb cast, and
        # reads come back already-parsed. SQLite stores/returns plain TEXT.
        self._jsonb = "::jsonb" if placeholder == "%s" else ""

    def _q(self, sql: str) -> str:
        return sql.replace("?", self.ph)

    def init_schema(self) -> None:
        """SQLite/dry-run convenience only. On Postgres the 0001 migration already owns audit_logs."""
        cur = self.conn.cursor()
        cur.execute(AUDIT_DDL)
        self.conn.commit()

    # ---- low-level append (INSERT-only; never UPDATE/DELETE — affos_service cannot) ----
    def _append(self, event: str, target: Optional[str], meta: Dict) -> str:
        rid = "cost_" + uuid.uuid4().hex[:16]
        cur = self.conn.cursor()
        cur.execute(self._q(
            "INSERT INTO audit_logs (id, event, actor, target, meta, ts) "
            "VALUES (?, ?, ?, ?, ?" + self._jsonb + ", ?)"),
            (rid, event, meta.get("actor"), target, json.dumps(meta, ensure_ascii=False), _now_iso()))
        self.conn.commit()
        return rid

    def _has_call(self, call_id: str) -> bool:
        """Best-effort write-side dedup probe (Option A): is this call_id already logged? Race-prone by
        design (see module docstring); read-time dedup is the authoritative guard."""
        return any(m.get("call_id") == call_id for _ev, m, _ts in self._raw((COST_EVENT,)))

    # ---- write ----
    def record_call(self, *, step: str, model: Optional[str] = None, provider: Optional[str] = None,
                    in_tokens: int = 0, out_tokens: int = 0,
                    unit_cost_in: Optional[float] = None, unit_cost_out: Optional[float] = None,
                    usd: Optional[float] = None, estimated_usd: Optional[float] = None,
                    job_id: Optional[str] = None, video_id: Optional[str] = None,
                    run_id: Optional[str] = None, call_id: Optional[str] = None,
                    idempotency_key: Optional[str] = None, attempt: int = 1, status: str = "success",
                    usage_source: str = "ESTIMATED", cost_state: Optional[str] = None,
                    actor: Optional[str] = None, cache_hit: bool = False, deduped: bool = False,
                    phase: str = "baseline", skip_if_logged: bool = False) -> str:
        """Record one metered call (append-only). Returns the call_id (pass it to confirm_cost later).

        estimated_usd: if not given, falls back to `usd`, else price*tokens; if no basis, stays None
        (never fabricated). confirmed billed cost is NOT set here — use confirm_cost() (a separate row).
        call_id defaults to a unique id (so distinct attempts never collide); pass it explicitly to log a
        pending→terminal lifecycle or to detect a duplicate. skip_if_logged=True does a best-effort probe
        and returns the existing id without inserting when the call_id is already present."""
        if estimated_usd is None:
            if usd is not None:
                estimated_usd = float(usd)
            elif unit_cost_in is not None or unit_cost_out is not None:
                estimated_usd = round(in_tokens * (unit_cost_in or 0.0) + out_tokens * (unit_cost_out or 0.0), 6)
        if call_id is None:
            call_id = "call_" + uuid.uuid4().hex[:16]
        if idempotency_key is None and run_id is not None and video_id is not None:
            idempotency_key = f"{run_id}:{step}:{video_id}"
        if cost_state is None:
            cost_state = "ESTIMATED" if estimated_usd is not None else "UNKNOWN"
        if skip_if_logged and self._has_call(call_id):
            return call_id  # best-effort idempotent logging; read-time dedup is authoritative
        meta = {
            "call_id": call_id, "run_id": run_id, "idempotency_key": idempotency_key,
            "attempt": int(attempt), "status": status,
            "job_id": job_id, "video_id": video_id, "step": step, "model": model, "provider": provider,
            "in_tokens": int(in_tokens), "out_tokens": int(out_tokens),
            "unit_cost_in": unit_cost_in, "unit_cost_out": unit_cost_out,
            "usage_source": usage_source, "cost_state": cost_state,
            "estimated_usd": estimated_usd, "confirmed_billed_usd": None,
            "usd": estimated_usd,   # back-compat mirror of the effective pre-confirmation cost
            "cache_hit": bool(cache_hit), "deduped": bool(deduped), "phase": phase, "actor": actor,
        }
        self._append(COST_EVENT, video_id, meta)
        return call_id   # the caller uses this for confirm_cost(call_id, ...)

    def confirm_cost(self, call_id: str, confirmed_billed_usd: float, actor: Optional[str] = None,
                     usage_source: str = "PROVIDER_REPORTED") -> str:
        """Append a billed-cost confirmation for a prior call_id (a SEPARATE row — no UPDATE, RLS-safe).
        Read-time, this overrides the estimate for that call_id."""
        meta = {"call_id": call_id, "confirmed_billed_usd": float(confirmed_billed_usd),
                "usage_source": usage_source, "cost_state": "CONFIRMED_BILLED", "actor": actor}
        return self._append(CONFIRM_EVENT, call_id, meta)

    # ---- read ----
    def _raw(self, events: Tuple[str, ...]) -> List[Tuple[str, Dict, object]]:
        """(event, parsed-meta, ts) for the given events, oldest->newest. ORDER BY ts, id makes 'latest
        wins' deterministic for duplicate cost.confirm rows AND stable on an exact-ts tie (id is the PK,
        a repeatable secondary sort). ISO-8601 UTC text sorts chronologically; PG timestamptz sorts
        natively. (SQLite TEXT -> json.loads; PG jsonb -> already dict.)"""
        marks = ",".join(["?"] * len(events))
        cur = self.conn.cursor()
        cur.execute(self._q(f"SELECT event, meta, ts FROM audit_logs WHERE event IN ({marks}) ORDER BY ts, id"),
                    tuple(events))
        out: List[Tuple[str, Dict, object]] = []
        for row in cur.fetchall():
            ev = row[0] if not isinstance(row, dict) else row["event"]
            meta = row[1] if not isinstance(row, dict) else row["meta"]
            ts = row[2] if not isinstance(row, dict) else row["ts"]
            out.append((ev, meta if isinstance(meta, dict) else json.loads(meta), ts))
        return out

    @staticmethod
    def _rank(r: Dict) -> Tuple[int, int]:
        """Terminal (success/failed) beats pending; higher attempt wins ties."""
        return (1 if r.get("status") in _TERMINAL else 0, int(r.get("attempt") or 1))

    def _read(self) -> Tuple[List[Dict], List[Dict]]:
        """Return (deduped cost rows, orphan confirmations). Rows are read ORDER BY ts, so for duplicate
        cost.confirm rows on one call_id the LATEST by ts wins (deterministic). Collapse cost.call rows
        that share a call_id to the terminal attempt; rows without a call_id (legacy) pass through; apply
        cost.confirm overrides by call_id. An orphan confirm (a call_id with no cost.call row) is NOT
        applied to any cost and is returned separately so it is surfaced, not silently dropped."""
        by_call: Dict[str, Dict] = {}
        passthrough: List[Dict] = []
        confirms: Dict[str, float] = {}
        for ev, m, ts in self._raw((COST_EVENT, CONFIRM_EVENT)):
            if ev == CONFIRM_EVENT:
                cid = m.get("call_id")
                cb = m.get("confirmed_billed_usd")
                if cid is not None and cb is not None:
                    confirms[cid] = float(cb)   # rows are (ts,id)-ordered -> latest confirmation wins
                continue
            m["_ts"] = ts                       # ephemeral: the audit_logs.ts, for pending-age (not persisted)
            cid = m.get("call_id")
            if cid is None:
                passthrough.append(m)
                continue
            prev = by_call.get(cid)
            if prev is None or self._rank(m) >= self._rank(prev):
                by_call[cid] = m
        rows: List[Dict] = passthrough + list(by_call.values())
        present = {r.get("call_id") for r in rows if r.get("call_id") is not None}
        out: List[Dict] = []
        for m in rows:
            cid = m.get("call_id")
            if cid in confirms:
                m = dict(m)
                m["confirmed_billed_usd"] = confirms[cid]
                m["cost_state"] = "CONFIRMED_BILLED"
            out.append(m)
        orphans = [{"call_id": cid, "confirmed_billed_usd": confirms[cid]}
                   for cid in confirms if cid not in present]
        return out, orphans

    def _dedup_rows(self) -> List[Dict]:
        """Deduped cost rows only (orphan confirms dropped — see _read / summary.orphan_confirms)."""
        return self._read()[0]

    @staticmethod
    def _agg(rows: List[Dict]) -> Dict:
        effective = [(_effective(r), r) for r in rows]
        priced = [(v, r) for v, r in effective if v is not None]
        confirmed = [r for r in rows if r.get("confirmed_billed_usd") is not None]
        confirmed_usd = round(sum(float(r["confirmed_billed_usd"]) for r in confirmed), 6)
        est_only = [r for r in rows if r.get("confirmed_billed_usd") is None and _estimated(r) is not None]
        estimated_only_usd = round(sum(_estimated(r) for r in est_only), 6)
        usd = round(sum(v for v, _ in priced), 6)
        return {
            "calls": len(rows),
            "in_tokens": sum(int(r.get("in_tokens") or 0) for r in rows),
            "out_tokens": sum(int(r.get("out_tokens") or 0) for r in rows),
            "usd": usd,                                   # effective cost (confirmed where known, else estimated)
            "confirmed_usd": confirmed_usd,
            "estimated_only_usd": estimated_only_usd,
            "pct_confirmed": (round(confirmed_usd / usd, 4) if usd > 0 else None),
            "usd_priced_calls": len(priced),
            "usd_unpriced_calls": len(rows) - len(priced),   # usd total complete ONLY if this is 0
            "cache_hits": sum(1 for r in rows if r.get("cache_hit")),
            "deduped": sum(1 for r in rows if r.get("deduped")),
        }

    def cost_per_video(self, video_id: str) -> Dict:
        rows = [r for r in self._dedup_rows() if r.get("video_id") == video_id]
        return {"video_id": video_id, **self._agg(rows)}

    def cost_per_workflow(self, job_id: str) -> Dict:
        rows = [r for r in self._dedup_rows() if r.get("job_id") == job_id]
        return {"job_id": job_id, **self._agg(rows)}

    def summary(self, now: Optional[datetime] = None, stale_after_seconds: int = 86400) -> Dict:
        """Totals plus per-video and per-workflow roll-ups — the Phase-0 baseline report shape.

        orphan_confirms surfaces cost.confirm rows whose call_id has no matching cost.call (a billed
        amount that cannot be attributed — visible, not silently lost).

        pending surfaces cost.call rows still in status 'pending' (no terminal success/failed arrived),
        with age and a configurable stale threshold. This is READ-ONLY diagnostics: it never writes, never
        marks a stale call as failed, and never assumes a missing cost is 0 (unpriced pending stay unpriced)."""
        rows, orphans = self._read()
        videos = sorted({r.get("video_id") for r in rows if r.get("video_id") is not None})
        jobs = sorted({r.get("job_id") for r in rows if r.get("job_id") is not None})
        now = now or datetime.now(timezone.utc)

        pending = [r for r in rows if r.get("status") == "pending"]   # terminal rows already won in _read
        ages = {id(r): (now - _parse_ts(r.get("_ts"))).total_seconds()
                for r in pending if _parse_ts(r.get("_ts")) is not None}
        stale = [r for r in pending if ages.get(id(r), 0.0) >= stale_after_seconds]
        return {
            "totals": self._agg(rows),
            "per_video": {v: self._agg([r for r in rows if r.get("video_id") == v]) for v in videos},
            "per_workflow": {j: self._agg([r for r in rows if r.get("job_id") == j]) for j in jobs},
            "orphan_confirms": {
                "count": len(orphans),
                "usd": round(sum(o["confirmed_billed_usd"] for o in orphans), 6),
                "call_ids": [o["call_id"] for o in orphans],
            },
            "pending": {
                "count": len(pending),
                "stale_count": len(stale),
                "stale_after_seconds": stale_after_seconds,
                "oldest_age_seconds": round(max(ages.values()), 3) if ages else 0.0,
                "stale_call_ids": [r.get("call_id") for r in stale],
                "unpriced_count": sum(1 for r in pending if _effective(r) is None),  # cost NOT assumed 0
            },
        }
