"""QA — AFFOS real provider-runner (COST-1). Offline; mock adapters -> ZERO real cost.

Proves the dry-run safety gate (disabled by default; needs live + credential + adapter), free-stage pass-through,
usage capture, and the full MODE-B flow: baseline through the provider runner + reconcile billed -> pct_confirmed.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, "..", "apps", "content-factory", "pipeline")))

import cost_ledger            # noqa: E402
from provider_runner import (ProviderRunner, ProvidersDisabled, mock_adapters, reconcile_billed,  # noqa: E402
                             live_from_env, CREDENTIAL_ENV)
from baseline_runner import run_baseline, build_report, default_topics  # noqa: E402
from pipeline import ContentPipeline  # noqa: E402

CREDS = {v: "x" for v in CREDENTIAL_ENV.values()}      # all provider creds present (test env)


def _led():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?"); led.init_schema(); return led


class TestSafetyGate(unittest.TestCase):
    def test_disabled_by_default_refuses_paid_stage(self):
        run = ProviderRunner(mock_adapters(), env={}).factory()("topic-x")   # live defaults False
        with self.assertRaises(ProvidersDisabled):
            run("video")

    def test_free_stage_passes_through_even_when_disabled(self):
        run = ProviderRunner(mock_adapters(), env={}).factory()("topic-x")
        self.assertEqual(run("research"), "[free:research]")                 # no provider, no cost

    def test_live_requires_credential(self):
        run = ProviderRunner(mock_adapters(), live=True, env={}).factory()("topic-x")   # no creds
        with self.assertRaises(ProvidersDisabled):
            run("video")

    def test_live_requires_adapter(self):
        run = ProviderRunner({}, live=True, env=CREDS).factory()("topic-x")  # creds ok, no adapter
        with self.assertRaises(ProvidersDisabled):
            run("video")

    def test_live_from_env_switch(self):
        self.assertFalse(live_from_env({}))
        self.assertFalse(live_from_env({"AFFOS_PROVIDERS_LIVE": "0"}))
        self.assertTrue(live_from_env({"AFFOS_PROVIDERS_LIVE": "1"}))


class TestLiveWithMockAdapters(unittest.TestCase):
    def test_returns_artifact_and_records_usage(self):
        sink = []
        run = ProviderRunner(mock_adapters(), live=True, env=CREDS, usage_sink=sink).factory()("AI topic")
        art = run("video")
        self.assertEqual(art, "[elevenlabs:video:AI topic]")
        self.assertEqual(len(sink), 1)
        self.assertEqual(sink[0]["provider"], "elevenlabs")
        self.assertAlmostEqual(sink[0]["billed_usd"], 0.30, places=6)


class TestModeBFlowOffline(unittest.TestCase):
    def test_baseline_through_provider_runner_then_reconcile(self):
        led = _led()
        sink = []
        topics = default_topics(2)
        pr = ProviderRunner(mock_adapters(), live=True, env=CREDS, usage_sink=sink)
        results = run_baseline(led, topics=topics, real_runner_factory=pr.factory(),
                               pipeline_factory=ContentPipeline,
                               stage_cost={"script": 0.02, "thumbnail": 0.05, "video": 0.30},
                               ceilings={"per_baseline_usd": 100.0})
        # before reconcile: estimates only
        self.assertEqual(build_report(led, results)["pct_confirmed"], 0.0)
        # reconcile billed from the provider usage sink -> confirmations
        n = reconcile_billed(led, sink, topics)
        self.assertEqual(n, 2 * 4)                       # 4 paid stages (script/thumbnail/video/publish) x 2 videos
        rep = build_report(led, results)
        self.assertGreater(rep["pct_confirmed"], 0.0)    # now billed cost dominates
        # publish (vidiq) bills $0.00, so confirmed total = 2 x (0.02+0.05+0.30+0.00)
        self.assertAlmostEqual(rep["totals"]["confirmed_usd"], 2 * (0.02 + 0.05 + 0.30 + 0.00), places=6)


if __name__ == "__main__":
    unittest.main()
