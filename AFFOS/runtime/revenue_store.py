"""AFFOS Revenue durable store (S5A — additive). Persists ingestion approvals, request-level
idempotency and audit so they survive application restart and are safe under concurrency.

One code path for both engines: all SQL uses `ON CONFLICT ... DO NOTHING`, which SQLite (3.24+)
and PostgreSQL both support; only the parameter placeholder differs ("?" vs "%s"). The SQLite path
is the TEST/DRY-RUN adapter and is fully exercised by tests; production uses the identical DDL in
`core/schema/0004_revenue_ingest.sql` on Postgres (applied on the VPS under a separate approval).

Concurrency: idempotency reservation is a single atomic INSERT with ON CONFLICT DO NOTHING, so two
concurrent requests with the same key produce exactly one logical operation — the loser reads the
stored row. Restart: rows live in the DB, not in process memory.

Reuses the existing `audit_logs` table (no new audit engine). No secret is read or printed.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

APPROVALS_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_approvals (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  environment TEXT NOT NULL,
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  granted_by TEXT,
  granted_at TEXT NOT NULL,
  revoked_by TEXT,
  revoked_at TEXT
);
"""
APPROVALS_IDX = (
    "CREATE INDEX IF NOT EXISTS ix_appr_lookup "
    "ON ingestion_approvals(provider, environment, status);"
)
IDEMPOTENCY_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_idempotency (
  idem_key TEXT PRIMARY KEY,
  body_hash TEXT NOT NULL,
  response TEXT,
  created_at TEXT NOT NULL
);
"""
# Defense-in-depth row-level dedupe: a provider action id can back at most one commission.
COMMISSION_UNIQUE_IDX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_commissions_src "
    "ON commissions(source, source_record_id);"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(dt) -> str:
    return dt.isoformat() if isinstance(dt, datetime) else str(dt)


class RevenueStore:
    """DB-backed store. `conn` is a DB-API connection (sqlite3 in tests; psycopg in prod).
    `placeholder` is "?" for SQLite, "%s" for Postgres."""

    def __init__(self, conn, placeholder: str = "?"):
        self.conn = conn
        self.ph = placeholder

    # ---- schema (SQLite/dry-run convenience; prod uses the 0004 migration) ----
    def init_schema(self, with_commission_unique: bool = True) -> None:
        cur = self.conn.cursor()
        cur.execute(APPROVALS_DDL)
        cur.execute(APPROVALS_IDX)
        cur.execute(IDEMPOTENCY_DDL)
        if with_commission_unique:
            cur.execute(COMMISSION_UNIQUE_IDX)
        self.conn.commit()

    def _q(self, sql: str) -> str:
        return sql.replace("?", self.ph)

    # ---- idempotency (two-layer, concurrency-safe) ----
    def reserve(self, idem_key: str, body_hash: str) -> Tuple[str, Optional[Dict]]:
        """Atomically reserve a key. Returns:
          ("new", None)            — caller should run and then commit_response()
          ("replay", response)     — same key + same body already processed
          ("conflict", None)       — same key + different body
        """
        cur = self.conn.cursor()
        cur.execute(self._q(
            "INSERT INTO ingestion_idempotency (idem_key, body_hash, response, created_at) "
            "VALUES (?, ?, NULL, ?) ON CONFLICT (idem_key) DO NOTHING"),
            (idem_key, body_hash, _now_iso()))
        self.conn.commit()
        if cur.rowcount == 1:
            return "new", None
        cur.execute(self._q(
            "SELECT body_hash, response FROM ingestion_idempotency WHERE idem_key = ?"), (idem_key,))
        row = cur.fetchone()
        stored_hash, resp = (row[0], row[1]) if not isinstance(row, dict) else (row["body_hash"], row["response"])
        if stored_hash != body_hash:
            return "conflict", None
        return "replay", (json.loads(resp) if resp else None)

    def commit_response(self, idem_key: str, response: Dict) -> None:
        cur = self.conn.cursor()
        cur.execute(self._q("UPDATE ingestion_idempotency SET response = ? WHERE idem_key = ?"),
                    (json.dumps(response, ensure_ascii=False), idem_key))
        self.conn.commit()

    # ---- approvals ----
    def add_approval(self, provider: str, environment: str, window_start, window_end,
                     expires_at, granted_by: Optional[str]) -> Dict:
        rec = {
            "id": "appr_" + uuid.uuid4().hex[:16], "provider": provider, "environment": environment,
            "window_start": _iso(window_start), "window_end": _iso(window_end),
            "expires_at": _iso(expires_at), "status": "active",
            "granted_by": granted_by, "granted_at": _now_iso(),
            "revoked_by": None, "revoked_at": None,
        }
        cur = self.conn.cursor()
        cur.execute(self._q(
            "INSERT INTO ingestion_approvals "
            "(id, provider, environment, window_start, window_end, expires_at, status, granted_by, granted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"),
            (rec["id"], provider, environment, rec["window_start"], rec["window_end"],
             rec["expires_at"], "active", granted_by, rec["granted_at"]))
        self.conn.commit()
        return rec

    def revoke_approval(self, approval_id: str, actor: Optional[str]) -> bool:
        cur = self.conn.cursor()
        cur.execute(self._q(
            "UPDATE ingestion_approvals SET status='revoked', revoked_by=?, revoked_at=? "
            "WHERE id=? AND status='active'"), (actor, _now_iso(), approval_id))
        self.conn.commit()
        return cur.rowcount == 1

    def is_approved(self, provider: str, environment: str, now) -> bool:
        now_iso = _iso(now)
        cur = self.conn.cursor()
        cur.execute(self._q(
            "SELECT 1 FROM ingestion_approvals WHERE provider=? AND environment=? AND status='active' "
            "AND window_start <= ? AND window_end >= ? AND expires_at > ? LIMIT 1"),
            (provider, environment, now_iso, now_iso, now_iso))
        return cur.fetchone() is not None

    # ---- conversion chain write: ONE transaction, deterministic ids, row-level dedupe ----
    def write_conversion_chain(self, action: Dict, data_state: str = "DRY_RUN") -> bool:
        """Write click -> conversion -> commission for one provider action in a SINGLE transaction.
        Ids are deterministic (CE-/CV-/CO-{source_record_id}); the unique(source, source_record_id)
        index makes a duplicate action a no-op/raise rather than a duplicate commission. On any error
        the whole chain rolls back (no partial write) — safe recovery is to replay the same action.

        NOTE: this is an additive helper that mirrors the reused AWIN/Impact engines' write shape;
        it does not replace them. Wiring the live engines to call it is a later sprint (dry-run writes
        nothing today). Requires the commission unique index (init_schema(with_commission_unique=True))."""
        src = action["source"]
        srid = str(action["source_record_id"])
        ce, cv, co = f"CE-{srid}", f"CV-{srid}", f"CO-{srid}"
        cur = self.conn.cursor()
        try:
            cur.execute(self._q(
                "INSERT INTO click_events (id, tracking_link_id, ts, event_subtype, source, "
                "source_record_id, data_state, currency, is_verified) VALUES (?,?,?,?,?,?,?,?,0) "
                "ON CONFLICT (id) DO NOTHING"),
                (ce, action.get("tracking_link_id", ""), action.get("ts", ""), "SEEDED_CLICK",
                 src, srid, data_state, action.get("currency", "VND")))
            cur.execute(self._q(
                "INSERT INTO conversion_events (id, click_event_id, offer_id, order_value, status, "
                "ts, source, source_record_id, data_state, currency, is_verified) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,0) ON CONFLICT (id) DO NOTHING"),
                (cv, ce, action.get("offer_id", ""), action.get("order_value", 0),
                 action.get("status", "pending"), action.get("ts", ""), src, srid, data_state,
                 action.get("currency", "VND")))
            cur.execute(self._q(
                "INSERT INTO commissions (id, conversion_event_id, amount, status, source, "
                "source_record_id, data_state, currency, is_verified) VALUES (?,?,?,?,?,?,?,?,0)"),
                (co, cv, action.get("commission_amount", 0), action.get("status", "pending"),
                 src, srid, data_state, action.get("currency", "VND")))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise

    # ---- audit (reuse audit_logs) ----
    def audit(self, event: str, actor: Optional[str], target: Optional[str], meta: Dict) -> None:
        cur = self.conn.cursor()
        cur.execute(self._q(
            "INSERT INTO audit_logs (id, event, actor, target, meta, ts) VALUES (?, ?, ?, ?, ?, ?)"),
            ("aud_" + uuid.uuid4().hex[:16], event, actor, target,
             json.dumps(meta, ensure_ascii=False), _now_iso()))
        self.conn.commit()
