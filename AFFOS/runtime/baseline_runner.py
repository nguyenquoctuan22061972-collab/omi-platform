"""AFFOS COST-1 baseline harness (Phase-0). Runs N SEQUENTIAL AI-Automation videos through the content
pipeline, metering each stage into the CostLedger and enforcing spend ceilings, then builds a baseline
report (cost/video, cost/workflow, pct_confirmed, pending/orphan diagnostics).

DRY-RUN SAFE: no paid call lives here. The caller supplies `real_runner_factory(topic) -> runner(stage)`;
only that runner can make a real provider call. In the pilot/tests it is the pipeline's mock runner
(zero cost). At real execution the caller swaps in the real providers and points the ledger at the
staging DB: `CostLedger(psycopg.connect(SVC_URL), "%s")` (least-privilege affos_service, INSERT-only).

SEQUENTIAL by construction: the per-connector/per-baseline ceilings are enforced from the durable ledger
and are strict only when runs are sequential (true-parallel runs need a DB counter/lock — out of Phase-0).
No savings % is produced — Phase-0 yields only the baseline denominator. No secret is read or logged.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Dict, List, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)
from pilot_metering import metered_runner, CeilingExceeded  # noqa: E402

# Illustrative defaults — ESTIMATES / CAPS, not verified pricing. Override at call sites.
DEFAULT_STAGE_COST: Dict[str, float] = {"script": 0.02, "thumbnail": 0.05, "video": 0.30}
DEFAULT_CEILINGS: Dict = {
    "per_run_usd": 1.00,
    "per_connector_usd": {"model": 0.50, "canva": 0.75, "elevenlabs": 2.00},  # baseline-wide (cumulative)
    "per_baseline_usd": 3.00,
}
DEFAULT_JOB_ID = "wf_content_factory"


def default_topics(n: int = 5) -> List[str]:
    return [f"AI Automation #{i + 1}" for i in range(n)]


def run_baseline(ledger, *, topics: List[str], real_runner_factory: Callable[[str], Callable[[str], str]],
                 pipeline_factory: Callable[[str], object], stage_cost: Optional[Dict] = None,
                 ceilings: Optional[Dict] = None, job_id: str = DEFAULT_JOB_ID,
                 usage_source: str = "ESTIMATED") -> List[Dict]:
    """Run each topic's video SEQUENTIALLY through `pipeline_factory(topic).run_all(runner=...)`, metering
    into `ledger`. A ceiling breach stops that run (recorded, not a silent drop) and the loop continues.
    Returns a per-run summary list."""
    stage_cost = DEFAULT_STAGE_COST if stage_cost is None else stage_cost
    ceilings = DEFAULT_CEILINGS if ceilings is None else ceilings
    results: List[Dict] = []
    for i, topic in enumerate(topics):
        run_id, video_id = f"r{i + 1}", f"V{i + 1}"
        pipe = pipeline_factory(topic)
        runner = metered_runner(ledger, run_id=run_id, video_id=video_id, job_id=job_id,
                                real_runner=real_runner_factory(topic), stage_cost=stage_cost,
                                ceilings=ceilings, usage_source=usage_source, phase="baseline")
        status = "done"
        try:
            pipe.run_all(runner=runner)
        except CeilingExceeded as exc:
            status = f"CEILING_STOP: {exc}"
        cpv = ledger.cost_per_video(video_id)
        results.append({"run_id": run_id, "video_id": video_id, "topic": topic, "status": status,
                        "usd": cpv["usd"], "calls": cpv["calls"], "unpriced": cpv["usd_unpriced_calls"]})
    return results


def build_report(ledger, results: List[Dict], job_id: str = DEFAULT_JOB_ID) -> Dict:
    """The Phase-0 baseline report: cost/video (median + range), cost/workflow, totals, and diagnostics.
    No savings % — this is only the baseline denominator."""
    s = ledger.summary()
    per_video = [r["usd"] for r in results]
    srt = sorted(per_video)
    median = srt[len(srt) // 2] if srt else 0.0
    return {
        "baseline": {
            "N": len(results),
            "cost_per_video_usd": per_video,
            "median_cost_per_video_usd": median,
            "range_usd": [min(per_video), max(per_video)] if per_video else [0.0, 0.0],
        },
        "cost_per_workflow_usd": ledger.cost_per_workflow(job_id)["usd"],
        "totals": s["totals"],
        "pct_confirmed": s["totals"]["pct_confirmed"],
        "pending": s["pending"],
        "orphan_confirms": s["orphan_confirms"],
        "runs": results,
    }


def _default_pipeline_factory():
    """Resolve the content pipeline (apps/content-factory/pipeline) for the __main__ dry-run."""
    sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "apps", "content-factory", "pipeline")))
    from pipeline import ContentPipeline  # noqa: E402
    return ContentPipeline


def main() -> int:
    """DRY-RUN: sqlite ledger + the pipeline's MOCK runner -> ZERO real cost. Prints a sample report."""
    import json
    import sqlite3
    import cost_ledger
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?")
    led.init_schema()
    ContentPipeline = _default_pipeline_factory()
    topics = default_topics(5)
    results = run_baseline(led, topics=topics,
                           real_runner_factory=lambda topic: (lambda stage: f"[mock:{stage}]"),
                           pipeline_factory=ContentPipeline)
    print(json.dumps(build_report(led, results), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
