"""AFFOS Token/Cost Ledger — Phase 0 (additive, measurement-only).

Purpose: capture a per-call cost/token record so a baseline cost/video and cost/workflow can be measured
BEFORE any optimization. Phase 0 is measurement ONLY — it does not change any pipeline behavior.

Design (approved Phase-0 spec):
  * NO new database and NO new table — rows are written to the EXISTING `audit_logs` table
    (id, event, actor, target, meta jsonb, ts), reusing the exact path RevenueStore.audit() uses.
    `event='cost.call'`, `target=<video_id>`, `meta=<the cost record>`.
  * NO new privilege — the least-privilege runtime role already has INSERT on audit_logs (migration 0005).
    This module writes nowhere else, so Phase-0 needs no additional grant, no service_role, no BYPASSRLS.
  * One code path for SQLite (tests/dry-run) and Postgres (prod): only the placeholder ("?" vs "%s") and the
    jsonb cast differ, exactly like RevenueStore.

Honesty rule baked in: if a call has no unit price, `usd` stays None — cost is NEVER fabricated. Aggregations
sum only priced calls and separately report how many calls were unpriced, so a total is never silently low.
No secret is read or printed.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

COST_EVENT = "cost.call"

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

    # ---- write ----
    def record_call(self, *, step: str, model: Optional[str] = None,
                    in_tokens: int = 0, out_tokens: int = 0,
                    unit_cost_in: Optional[float] = None, unit_cost_out: Optional[float] = None,
                    usd: Optional[float] = None, job_id: Optional[str] = None,
                    video_id: Optional[str] = None, actor: Optional[str] = None,
                    cache_hit: bool = False, deduped: bool = False, phase: str = "baseline") -> str:
        """Record one metered call. Returns the audit_logs row id.

        usd: if not given but a unit price is, usd = in_tokens*unit_cost_in + out_tokens*unit_cost_out.
             If no price basis exists at all, usd stays None (never fabricated)."""
        if usd is None and (unit_cost_in is not None or unit_cost_out is not None):
            usd = round(in_tokens * (unit_cost_in or 0.0) + out_tokens * (unit_cost_out or 0.0), 6)
        meta = {
            "job_id": job_id, "video_id": video_id, "step": step, "model": model,
            "in_tokens": int(in_tokens), "out_tokens": int(out_tokens),
            "unit_cost_in": unit_cost_in, "unit_cost_out": unit_cost_out, "usd": usd,
            "cache_hit": bool(cache_hit), "deduped": bool(deduped), "phase": phase,
        }
        rid = "cost_" + uuid.uuid4().hex[:16]
        cur = self.conn.cursor()
        cur.execute(self._q(
            "INSERT INTO audit_logs (id, event, actor, target, meta, ts) "
            "VALUES (?, ?, ?, ?, ?" + self._jsonb + ", ?)"),
            (rid, COST_EVENT, actor, video_id, json.dumps(meta, ensure_ascii=False), _now_iso()))
        self.conn.commit()
        return rid

    # ---- read ----
    def _cost_rows(self) -> List[Dict]:
        """All cost.call records, meta parsed to dict (SQLite TEXT -> json.loads; PG jsonb -> already dict)."""
        cur = self.conn.cursor()
        cur.execute(self._q("SELECT meta FROM audit_logs WHERE event = ?"), (COST_EVENT,))
        out: List[Dict] = []
        for row in cur.fetchall():
            meta = row[0] if not isinstance(row, dict) else row["meta"]
            out.append(meta if isinstance(meta, dict) else json.loads(meta))
        return out

    @staticmethod
    def _agg(rows: List[Dict]) -> Dict:
        priced = [r for r in rows if r.get("usd") is not None]
        return {
            "calls": len(rows),
            "in_tokens": sum(int(r.get("in_tokens") or 0) for r in rows),
            "out_tokens": sum(int(r.get("out_tokens") or 0) for r in rows),
            "usd": round(sum(float(r["usd"]) for r in priced), 6),
            "usd_priced_calls": len(priced),
            "usd_unpriced_calls": len(rows) - len(priced),   # usd total is complete ONLY if this is 0
            "cache_hits": sum(1 for r in rows if r.get("cache_hit")),
            "deduped": sum(1 for r in rows if r.get("deduped")),
        }

    def cost_per_video(self, video_id: str) -> Dict:
        rows = [r for r in self._cost_rows() if r.get("video_id") == video_id]
        return {"video_id": video_id, **self._agg(rows)}

    def cost_per_workflow(self, job_id: str) -> Dict:
        rows = [r for r in self._cost_rows() if r.get("job_id") == job_id]
        return {"job_id": job_id, **self._agg(rows)}

    def summary(self) -> Dict:
        """Totals plus per-video and per-workflow roll-ups — the Phase-0 baseline report shape."""
        rows = self._cost_rows()
        videos = sorted({r.get("video_id") for r in rows if r.get("video_id") is not None})
        jobs = sorted({r.get("job_id") for r in rows if r.get("job_id") is not None})
        return {
            "totals": self._agg(rows),
            "per_video": {v: self._agg([r for r in rows if r.get("video_id") == v]) for v in videos},
            "per_workflow": {j: self._agg([r for r in rows if r.get("job_id") == j]) for j in jobs},
        }
