"""QA — AFFOS pilot metering (Phase-0 wiring). Offline SQLite; mock runner -> ZERO real cost.

Covers: per-stage cost.call logging through the content pipeline's runner hook; durable spend-ceiling
refusal (per-run / per-connector / per-baseline) with a recorded failed row; unpriced stage surfaced;
confirm_stage override; CONCERN-1 (retry re-bill is counted, no missing cost); CONCERN-2 (durable
ceilings make a second run see the first run's committed cost); dry-run via the real ContentPipeline.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, "..", "apps", "content-factory", "pipeline")))

import cost_ledger          # noqa: E402
from pilot_metering import metered_runner, confirm_stage, CeilingExceeded  # noqa: E402


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
        self.assertEqual(cpv["calls"], 2)                       # one call per stage (pending+success dedup)

    def test_unpriced_stage_surfaced_not_zero(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock, stage_cost={"script": 0.01})
        run("research")                                         # 'research' not priced
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["usd_unpriced_calls"], 1)
        self.assertEqual(cpv["usd_priced_calls"], 0)

    def test_confirm_stage_overrides_estimate(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock, stage_cost={"video": 0.30})
        run("video")
        confirm_stage(led, "r1", "video", 0.26)                 # attempt defaults to 1 -> r1:video#1
        cpv = led.cost_per_video("V1")
        self.assertAlmostEqual(cpv["usd"], 0.26, places=6)
        self.assertAlmostEqual(cpv["confirmed_usd"], 0.26, places=6)


class TestConcern1RetryNoMissingCost(unittest.TestCase):
    def test_each_real_provider_call_is_counted(self):
        _, led = _fresh()
        bills = {"video": 0}
        def paying(stage):              # a REAL provider call that bills each time
            bills[stage] += 1
            return f"[billed:{stage}#{bills[stage]}]"
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=paying, stage_cost={"video": 0.30})
        run("video")                    # attempt 1 (billed)
        run("video")                    # attempt 2 — retry that re-bills
        cpv = led.cost_per_video("V1")
        self.assertEqual(bills["video"], 2)
        self.assertEqual(cpv["calls"], 2)                       # both real charges recorded (no missing cost)
        self.assertAlmostEqual(cpv["usd"], 0.60, places=6)

    def test_single_invocation_pending_plus_success_dedup_to_one(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock, stage_cost={"video": 0.30})
        run("video")                    # logs pending then success with the SAME call_id (one real call)
        self.assertEqual(led.cost_per_video("V1")["calls"], 1)


class TestConcern2DurableCeilings(unittest.TestCase):
    def test_per_run_ceiling_refuses_and_records_failed(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock,
                             stage_cost={"video": 0.30}, ceilings={"per_run_usd": 0.20})
        with self.assertRaises(CeilingExceeded):
            run("video")                                        # 0.30 > 0.20 -> refuse
        rows = led._dedup_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "failed")
        self.assertEqual(led.cost_per_video("V1")["usd"], 0.0)  # refused stage adds NO cost

    def test_per_connector_ceiling_durable_across_invocations(self):
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=_mock,
                             stage_cost={"video": 0.30}, ceilings={"per_connector_usd": {"elevenlabs": 0.50}})
        run("video")                                            # elevenlabs 0.30 committed (<=0.50)
        with self.assertRaises(CeilingExceeded):
            run("video")                                        # 0.30 committed + 0.30 = 0.60 > 0.50
        self.assertAlmostEqual(led.cost_by_provider()["elevenlabs"], 0.30, places=6)

    def test_per_baseline_ceiling_second_run_sees_first_runs_committed_cost(self):
        _, led = _fresh()                                       # one shared ledger = the durable source
        runA = metered_runner(led, run_id="rA", video_id="VA", real_runner=_mock,
                              stage_cost={"video": 0.60}, ceilings={"per_baseline_usd": 1.00})
        runB = metered_runner(led, run_id="rB", video_id="VB", real_runner=_mock,
                              stage_cost={"video": 0.60}, ceilings={"per_baseline_usd": 1.00})
        runA("video")                                          # commits 0.60
        with self.assertRaises(CeilingExceeded):
            runB("video")                                      # durable read: 0.60 + 0.60 > 1.00 -> refuse
        self.assertAlmostEqual(led.summary()["totals"]["usd"], 0.60, places=6)   # overrun prevented


class TestPipelineIntegrationDryRun(unittest.TestCase):
    def test_run_all_through_real_pipeline_is_mock_zero_real_cost(self):
        from pipeline import ContentPipeline
        _, led = _fresh()
        run = metered_runner(led, run_id="r1", video_id="V1", job_id="wf",
                             real_runner=ContentPipeline("AI Automation")._mock_run,
                             stage_cost={"script": 0.01, "thumbnail": 0.05, "video": 0.30},
                             ceilings={"per_run_usd": 2.0})
        p = ContentPipeline("AI Automation")
        out = p.run_all(runner=run)
        self.assertTrue(out["done"])
        self.assertTrue(all(a.startswith("[mock:") for a in out["artifacts"].values()))
        cpv = led.cost_per_video("V1")
        self.assertAlmostEqual(cpv["usd"], 0.36, places=6)      # 0.01 + 0.05 + 0.30 (paid stages only)
        self.assertEqual(cpv["usd_unpriced_calls"], 4)         # topic/research/qa/publish unpriced


if __name__ == "__main__":
    unittest.main()
