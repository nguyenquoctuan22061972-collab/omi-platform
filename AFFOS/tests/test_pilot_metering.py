"""QA — AFFOS pilot metering (Phase-0 wiring). Offline SQLite; mock runner -> ZERO real cost.

Covers: per-stage cost.call logging through the content pipeline's runner hook; spend-ceiling refusal
(per-run / per-connector / per-baseline) with a recorded failed row; unpriced stage surfaced; confirm_stage
override; idempotent call_id per run+stage; dry-run via the real ContentPipeline incurs no real call.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, "..", "apps", "content-factory", "pipeline")))

import cost_ledger          # noqa: E402
import pilot_metering       # noqa: E402
from pilot_metering import metered_runner, confirm_stage, CeilingExceeded, seed_tally  # noqa: E402


def _fresh():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?")
    led.init_schema()
    return conn, led


def _mock(stage):
    return f"[mock:{stage}]"      # no network, no cost


class TestMeteredRunner(unittest.TestCase):
    def test_logs_cost_per_paid_stage(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", job_id="wf",
                             real_runner=_mock, stage_cost={"script": 0.01, "video": 0.30})
        self.assertEqual(run("script"), "[mock:script]")
        run("video")
        cpv = led.cost_per_video("V1")
        self.assertAlmostEqual(cpv["usd"], 0.31, places=6)
        self.assertEqual(cpv["calls"], 2)                       # pending+success dedup to one per stage

    def test_unpriced_stage_surfaced_not_zero(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock,
                             stage_cost={"script": 0.01})        # 'research' not priced
        run("research")
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["usd_unpriced_calls"], 1)
        self.assertEqual(cpv["usd_priced_calls"], 0)

    def test_per_run_ceiling_refuses_and_records_failed(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock,
                             stage_cost={"video": 0.30}, ceilings={"per_run_usd": 0.20})
        with self.assertRaises(CeilingExceeded):
            run("video")                                        # 0.30 > 0.20 -> refuse
        # a failed row is recorded (never a silent drop); no success row, artifact not produced
        rows = led._dedup_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "failed")

    def test_per_connector_ceiling(self):
        _, led = _fresh()
        tally = seed_tally(led)
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock,
                             stage_cost={"video": 0.30, "thumbnail": 0.05},
                             ceilings={"per_connector_usd": {"elevenlabs": 0.25}}, tally=tally)
        with self.assertRaises(CeilingExceeded):
            run("video")                                        # elevenlabs 0.30 > 0.25
        run("thumbnail")                                        # canva unaffected -> ok
        self.assertAlmostEqual(led.cost_per_video("V1")["usd"], 0.05, places=6)

    def test_per_baseline_ceiling_across_tally(self):
        _, led = _fresh()
        tally = {"baseline_usd": 0.90, "connector_usd": {}}     # already spent 0.90 of the baseline
        run = metered_runner(led, run_id="r2", video_id="V2", real_runner=_mock,
                             stage_cost={"video": 0.30}, ceilings={"per_baseline_usd": 1.00}, tally=tally)
        with self.assertRaises(CeilingExceeded):
            run("video")                                        # 0.90 + 0.30 > 1.00

    def test_confirm_stage_overrides_estimate(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock,
                             stage_cost={"video": 0.30})
        run("video")
        confirm_stage(led, "r1", "video", 0.26)                 # real billed cheaper
        cpv = led.cost_per_video("V1")
        self.assertAlmostEqual(cpv["usd"], 0.26, places=6)
        self.assertAlmostEqual(cpv["confirmed_usd"], 0.26, places=6)

    def test_idempotent_call_id_per_run_stage(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock, stage_cost={"video": 0.30})
        run("video"); run("video")                              # same run+stage -> same call_id
        self.assertEqual(led.cost_per_video("V1")["calls"], 1)  # deduped, counted once


class TestPipelineIntegrationDryRun(unittest.TestCase):
    def test_run_all_through_real_pipeline_is_mock_zero_real_cost(self):
        from pipeline import ContentPipeline
        _, led = _fresh()
        tally = seed_tally(led)
        run = metered_runner(led, run_id="r1", video_id="V1", job_id="wf", real_runner=ContentPipeline("AI Automation")._mock_run,
                             stage_cost={"script": 0.01, "thumbnail": 0.05, "video": 0.30},
                             ceilings={"per_run_usd": 2.0}, tally=tally)
        p = ContentPipeline("AI Automation")
        out = p.run_all(runner=run)                             # drives all 7 stages through the metered runner
        self.assertTrue(out["done"])
        # artifacts are mock strings -> no real provider was called
        self.assertTrue(all(a.startswith("[mock:") for a in out["artifacts"].values()))
        cpv = led.cost_per_video("V1")
        self.assertAlmostEqual(cpv["usd"], 0.36, places=6)      # 0.01 + 0.05 + 0.30 (paid stages only)
        self.assertEqual(cpv["usd_unpriced_calls"], 4)         # topic/research/qa/publish unpriced


if __name__ == "__main__":
    unittest.main()
