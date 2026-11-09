"""AFFOS pilot metering — wires the content pipeline's runner hook into the CostLedger (Phase-0).

The content pipeline (apps/content-factory/pipeline/pipeline.py) runs each stage through an INJECTED
`runner(stage)->str`. `metered_runner(...)` returns such a runner that, around the real stage work:
  1. computes an estimated cost for the stage (from `stage_cost`; None -> unpriced, never fabricated),
  2. enforces spend ceilings BEFORE the stage (per-run from the durable ledger; per-connector and
     per-baseline from a caller-owned in-process `tally`). A would-be over-ceiling stage is REFUSED:
     it logs a `cost.call` with status='failed' and raises CeilingExceeded — it never runs the stage,
  3. logs a `pending` cost.call, then calls `real_runner(stage)` — the ONLY place a real paid call
     could occur — then logs the terminal `success`/`failed` cost.call (same call_id, dedup-safe),
  4. updates the tally and returns the artifact.

Dry-run safety: no paid call happens in this module. In the pilot/prep `real_runner` is the pipeline's
mock runner (zero cost); the paid baseline swaps in a real runner only under an explicit execution gate.
Append-only via the ledger (audit_logs) — no new DB/table/permission; no UPDATE/DELETE. Never logs secrets.

Ceiling scope note (honest): per-run is read from the durable ledger (authoritative, dedup/confirmed-aware).
per-connector and per-baseline use the caller-owned `tally`, which is exact within one process and, for a
multi-process baseline, must be seeded by the caller from the ledger (see `seed_tally`).
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

# Which pipeline stages are paid, and the connector each bills to. Other stages are free/cached.
DEFAULT_STAGE_CONNECTOR: Dict[str, str] = {"script": "model", "thumbnail": "canva", "video": "elevenlabs"}


class CeilingExceeded(RuntimeError):
    """A stage's estimated cost would push a run/connector/baseline total over its ceiling."""


def seed_tally(ledger) -> Dict:
    """A fresh tally seeded from the durable ledger's effective total (for cross-process baseline caps).
    per-connector seed is best-effort 0 (the ledger does not aggregate by connector); within one process
    the tally is exact as stages run."""
    try:
        base = float(ledger.summary()["totals"]["usd"])
    except Exception:
        base = 0.0
    return {"baseline_usd": base, "connector_usd": {}}


def _est(stage: str, stage_cost) -> Optional[float]:
    if stage_cost is None:
        return None
    v = stage_cost(stage) if callable(stage_cost) else stage_cost.get(stage)
    return None if v is None else float(v)


def metered_runner(ledger, *, run_id: str, video_id: str, job_id: Optional[str] = None,
                   real_runner: Callable[[str], str], stage_cost=None,
                   ceilings: Optional[Dict] = None, stage_connector: Optional[Dict[str, str]] = None,
                   tally: Optional[Dict] = None, usage_source: str = "ESTIMATED",
                   phase: str = "baseline") -> Callable[[str], str]:
    """Return a runner(stage)->str for ContentPipeline.advance/run_all that meters cost into `ledger`
    and enforces `ceilings`. `tally` (caller-owned, from seed_tally) tracks per-connector/per-baseline
    spend across stages/runs; omit it to skip those two caps (per-run still enforced from the ledger)."""
    conn_map = stage_connector or DEFAULT_STAGE_CONNECTOR

    def _log(stage, est, conn, status):
        ledger.record_call(step=stage, provider=conn, estimated_usd=est,
                           job_id=job_id, video_id=video_id, run_id=run_id,
                           call_id=f"{run_id}:{stage}", status=status,
                           usage_source=usage_source,
                           cost_state=("ESTIMATED" if est is not None else "UNKNOWN"), phase=phase)

    def _refuse(stage, est, conn, scope, cap):
        # A ceiling refusal happens BEFORE the provider call, so it costs nothing: record an UNPRICED
        # failed marker (est is a projection, not a charge; it stays in the raised error). This keeps
        # the ledger's "a failed PAID attempt may have billed" semantic for real post-call failures.
        _log(stage, None, conn, "failed")
        raise CeilingExceeded(f"{scope} ceiling {cap} would be exceeded at stage '{stage}' (est {est})")

    def runner(stage: str) -> str:
        est = _est(stage, stage_cost)
        conn = conn_map.get(stage)
        if est is not None and ceilings:
            # per-run: authoritative from the durable ledger (effective cost so far for this video)
            cap_run = ceilings.get("per_run_usd")
            if cap_run is not None and ledger.cost_per_video(video_id)["usd"] + est > cap_run + 1e-9:
                _refuse(stage, est, conn, "per_run_usd", cap_run)
            # per-connector: from the in-process tally
            cap_conn = (ceilings.get("per_connector_usd") or {}).get(conn)
            if cap_conn is not None and tally is not None:
                if tally.get("connector_usd", {}).get(conn, 0.0) + est > cap_conn + 1e-9:
                    _refuse(stage, est, conn, f"per_connector_usd[{conn}]", cap_conn)
            # per-baseline: from the in-process tally
            cap_base = ceilings.get("per_baseline_usd")
            if cap_base is not None and tally is not None:
                if tally.get("baseline_usd", 0.0) + est > cap_base + 1e-9:
                    _refuse(stage, est, conn, "per_baseline_usd", cap_base)
        _log(stage, est, conn, "pending")          # visible before the (possibly paid) call
        artifact = real_runner(stage)              # <-- the ONLY place a real paid call could occur
        _log(stage, est, conn, "success")          # terminal row (same call_id -> dedup keeps this)
        if est is not None and tally is not None:
            tally["baseline_usd"] = tally.get("baseline_usd", 0.0) + est
            if conn:
                tally.setdefault("connector_usd", {})
                tally["connector_usd"][conn] = tally["connector_usd"].get(conn, 0.0) + est
        return artifact

    return runner


def confirm_stage(ledger, run_id: str, stage: str, confirmed_billed_usd: float) -> str:
    """Reconcile a stage's real billed cost (a separate cost.confirm row; overrides the estimate at read)."""
    return ledger.confirm_cost(f"{run_id}:{stage}", confirmed_billed_usd)
