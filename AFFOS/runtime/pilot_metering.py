"""AFFOS pilot metering — wires the content pipeline's runner hook into the CostLedger (Phase-0).

The content pipeline (apps/content-factory/pipeline/pipeline.py) runs each stage through an INJECTED
`runner(stage)->str`. `metered_runner(...)` returns such a runner that, around the real stage work:
  1. computes an estimated cost for the stage (from `stage_cost`; None -> unpriced, never fabricated),
  2. enforces spend ceilings BEFORE the stage, read from the DURABLE ledger (so concurrent runs see each
     other's committed cost). A would-be over-ceiling stage is REFUSED: it logs an UNPRICED `failed`
     marker (a refusal is before the provider call, so it costs nothing) and raises CeilingExceeded,
  3. logs a `pending` cost.call, then calls `real_runner(stage)` — the ONLY place a real paid call could
     occur — then logs the terminal `success` cost.call. If `real_runner` RAISES, it instead logs a terminal
     `failed` cost.call (same call_id; estimate kept — a paid attempt may already have billed) and re-raises,
     so a crashed attempt is classified as failed (not left dangling 'pending') and no false success occurs,
  4. returns the artifact.

Concern-1 fix (retry / no missing cost): each PHYSICAL invocation of a stage gets a DISTINCT call_id
`f"{run_id}:{stage}#{attempt}"` (attempt increments per invocation). So a genuine retry that re-bills is
counted as a separate cost — never collapsed. The pending+success pair of ONE invocation share that
call_id, so a single real call is still logged idempotently (dedup-safe).

Concern-2 fix (ceiling race): per-run / per-connector / per-baseline caps are all enforced from the
DURABLE ledger (cost_per_video / cost_by_provider / summary totals), not an in-process tally, so a run
sees every prior committed cost. RESIDUAL: two truly-simultaneous runs can still both pass the check
before either commits (a narrow TOCTOU window); a STRICT guarantee needs a DB-enforced atomic counter
(a schema change, out of Phase-0) or an orchestrator lock — so run the baseline sequentially for a hard cap.

Dry-run safety: no paid call in this module. In the pilot/prep `real_runner` is the pipeline's mock
runner (zero cost). Append-only via the ledger (audit_logs) — no new DB/table/permission, no UPDATE/DELETE.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

# Which pipeline stages are paid, and the connector each bills to. Other stages are free/cached.
DEFAULT_STAGE_CONNECTOR: Dict[str, str] = {"script": "model", "thumbnail": "canva", "video": "elevenlabs"}


class CeilingExceeded(RuntimeError):
    """A stage's estimated cost would push a run/connector/baseline total over its ceiling."""


def _est(stage: str, stage_cost) -> Optional[float]:
    if stage_cost is None:
        return None
    v = stage_cost(stage) if callable(stage_cost) else stage_cost.get(stage)
    return None if v is None else float(v)


def metered_runner(ledger, *, run_id: str, video_id: str, job_id: Optional[str] = None,
                   real_runner: Callable[[str], str], stage_cost=None,
                   ceilings: Optional[Dict] = None, stage_connector: Optional[Dict[str, str]] = None,
                   usage_source: str = "ESTIMATED", phase: str = "baseline") -> Callable[[str], str]:
    """Return a runner(stage)->str for ContentPipeline.advance/run_all that meters cost into `ledger`
    and enforces `ceilings` from the durable ledger. Each physical stage invocation gets a distinct
    attempt/call_id so a retry that re-bills is never under-counted."""
    conn_map = stage_connector or DEFAULT_STAGE_CONNECTOR
    attempts: Dict[str, int] = {}

    def _log(stage, call_id, attempt, est, conn, status):
        ledger.record_call(step=stage, provider=conn, estimated_usd=est,
                           job_id=job_id, video_id=video_id, run_id=run_id,
                           call_id=call_id, attempt=attempt, status=status,
                           usage_source=usage_source,
                           cost_state=("ESTIMATED" if est is not None else "UNKNOWN"), phase=phase)

    def _ceiling_block(stage, est, conn):
        """Return (scope, cap) of the first ceiling a stage would breach (from the durable ledger), else None."""
        if est is None or not ceilings:
            return None
        cap_run = ceilings.get("per_run_usd")
        if cap_run is not None and ledger.cost_per_video(video_id)["usd"] + est > cap_run + 1e-9:
            return "per_run_usd", cap_run
        cap_conn = (ceilings.get("per_connector_usd") or {}).get(conn)
        if cap_conn is not None and ledger.cost_by_provider().get(conn, 0.0) + est > cap_conn + 1e-9:
            return f"per_connector_usd[{conn}]", cap_conn
        cap_base = ceilings.get("per_baseline_usd")
        if cap_base is not None and ledger.summary()["totals"]["usd"] + est > cap_base + 1e-9:
            return "per_baseline_usd", cap_base
        return None

    def runner(stage: str) -> str:
        attempts[stage] = attempts.get(stage, 0) + 1
        attempt = attempts[stage]
        call_id = f"{run_id}:{stage}#{attempt}"          # distinct per physical call -> retry re-bill counted
        est = _est(stage, stage_cost)
        conn = conn_map.get(stage)
        breach = _ceiling_block(stage, est, conn)
        if breach is not None:
            scope, cap = breach
            _log(stage, call_id, attempt, None, conn, "failed")   # unpriced marker: a refusal costs nothing
            raise CeilingExceeded(f"{scope} ceiling {cap} would be exceeded at stage '{stage}' (est {est})")
        _log(stage, call_id, attempt, est, conn, "pending")       # visible before the (possibly paid) call
        try:
            artifact = real_runner(stage)                         # <-- ONLY place a real paid call could occur
        except Exception:
            # The attempt reached the provider call and then failed. Record a TERMINAL 'failed' row for THIS
            # call_id (dedup keeps it over the 'pending') so a crashed attempt is classified as failed, not
            # left dangling as 'pending' (which would pollute stale-pending diagnostics forever). Keep the
            # estimate (a paid attempt may already have billed — cost is surfaced, never fabricated), then
            # re-raise so the caller sees the failure and no false success is produced.
            _log(stage, call_id, attempt, est, conn, "failed")
            raise
        _log(stage, call_id, attempt, est, conn, "success")       # terminal (same call_id -> dedup keeps this)
        return artifact

    return runner


def confirm_stage(ledger, run_id: str, stage: str, confirmed_billed_usd: float, attempt: int = 1) -> str:
    """Reconcile a stage attempt's real billed cost (a separate cost.confirm row; overrides the estimate
    at read). Defaults to attempt 1 (the single-attempt case); pass `attempt` to confirm a specific retry."""
    return ledger.confirm_cost(f"{run_id}:{stage}#{attempt}", confirmed_billed_usd)
