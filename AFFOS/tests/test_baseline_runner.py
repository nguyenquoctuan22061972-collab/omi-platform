"""QA — AFFOS COST-1 baseline harness. Offline SQLite; mock runner -> ZERO real cost.

Proves the harness runs N sequential videos through the real ContentPipeline, meters into the ledger,
enforces ceilings (self-stops on breach), and builds the Phase-0 baseline report — without any paid call.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, "..", "apps", "content-factory", "pipeline")))

import cost_ledger            # noqa: E402
import baseline_runner        # noqa: E402
from baseline_runner import run_baseline, build_report, default_topics  # noqa: E402
from pipeline import ContentPipeline  # noqa: E402


def _fresh():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?")
    led.init_schema()
    return led


def _mock_factory(topic):
    return lambda stage: f"[mock:{stage}]"      # no network, no cost


class TestBaselineHarness(unittest.TestCase):
    def test_five_sequential_runs_report_shape(self):
        led = _fresh()
        topics = default_topics(5)
        results = run_baseline(led, topics=topics, real_runner_factory=_mock_factory,
                               pipeline_factory=ContentPipeline,
                               stage_cost={"script": 0.02, "thumbnail": 0.05, "video": 0.30},
                               ceilings={"per_baseline_usd": 100.0})   # high cap -> all complete
        rep = build_report(led, results)
        self.assertEqual(rep["baseline"]["N"], 5)
        self.assertEqual(len(rep["baseline"]["cost_per_video_usd"]), 5)
        # each video = 0.02 + 0.05 + 0.30 = 0.37 ; workflow = 5 * 0.37 = 1.85
        self.assertAlmostEqual(rep["cost_per_workflow_usd"], 1.85, places=6)
        self.assertAlmostEqual(rep["baseline"]["median_cost_per_video_usd"], 0.37, places=6)
        self.assertTrue(all(r["status"] == "done" for r in results))
        self.assertEqual(rep["pct_confirmed"], 0.0)                    # nothing confirmed yet (estimates)

    def test_ceiling_self_stops_and_bounds_spend(self):
        led = _fresh()
        results = run_baseline(led, topics=default_topics(5), real_runner_factory=_mock_factory,
                               pipeline_factory=ContentPipeline,
                               stage_cost={"video": 0.30},
                               ceilings={"per_baseline_usd": 0.80})     # caps total at 0.80 -> stops after 2
        total = led.summary()["totals"]["usd"]
        self.assertLessEqual(total, 0.80 + 1e-9)                        # never overspends the baseline cap
        self.assertTrue(any(r["status"].startswith("CEILING_STOP") for r in results))

    def test_mock_runner_incurs_no_real_cost(self):
        led = _fresh()
        results = run_baseline(led, topics=default_topics(2), real_runner_factory=_mock_factory,
                               pipeline_factory=ContentPipeline)
        # all artifacts are mock strings via the pipeline -> no provider was called; report still builds
        rep = build_report(led, results)
        self.assertEqual(rep["baseline"]["N"], 2)
        self.assertIn("pending", rep)
        self.assertIn("orphan_confirms", rep)


if __name__ == "__main__":
    unittest.main()
