"""QA — AFFOS cost & live-mode GUARDS (Milestone 2, TASK 5). Negative tests proving a provider is never
called, and no cost is fabricated, outside the deliberately-enabled path. Offline; mock adapters / gated
ingest -> ZERO network, ZERO cost. No paid API is ever called.

Covers: live mode OFF by default; live requires BOTH the switch AND a credential AND a wired adapter;
free stages pass without a provider; ceiling refusal happens BEFORE any provider call and is UNPRICED
(a refusal costs nothing); AWIN live and Impact live are OFF (dry-run / needs approval); and no gate ever
reports a provider success it did not make.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))

import cost_ledger            # noqa: E402
from provider_runner import (ProviderRunner, ProvidersDisabled, mock_adapters,  # noqa: E402
                             live_from_env, CREDENTIAL_ENV)
from pilot_metering import metered_runner, CeilingExceeded  # noqa: E402
import awin_ingest            # noqa: E402
import impact_ingest          # noqa: E402
from awin_live import ProductionTransport  # noqa: E402

CREDS = {v: "x" for v in CREDENTIAL_ENV.values()}


def _led():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?"); led.init_schema(); return led


class TestLiveModeGuard(unittest.TestCase):
    def test_live_off_by_default_refuses_paid_stage(self):
        run = ProviderRunner(mock_adapters(), env={}).factory()("t")       # live defaults False
        with self.assertRaises(ProvidersDisabled):
            run("video")

    def test_live_requires_credential(self):
        run = ProviderRunner(mock_adapters(), live=True, env={}).factory()("t")   # live but no creds
        with self.assertRaises(ProvidersDisabled):
            run("video")

    def test_live_requires_wired_adapter(self):
        run = ProviderRunner({}, live=True, env=CREDS).factory()("t")       # creds ok, NO adapter
        with self.assertRaises(ProvidersDisabled):
            run("video")

    def test_free_stage_passes_without_provider(self):
        run = ProviderRunner(mock_adapters(), env={}).factory()("t")
        self.assertEqual(run("research"), "[free:research]")               # no provider, no cost

    def test_live_switch_only_on_explicit_1(self):
        self.assertFalse(live_from_env({}))
        self.assertFalse(live_from_env({"AFFOS_PROVIDERS_LIVE": "0"}))
        self.assertFalse(live_from_env({"AFFOS_PROVIDERS_LIVE": "true"}))
        self.assertTrue(live_from_env({"AFFOS_PROVIDERS_LIVE": "1"}))


class TestCeilingRefusalIsUnpricedAndBeforeCall(unittest.TestCase):
    def test_ceiling_refusal_costs_nothing_and_skips_provider(self):
        led = _led()
        called = {"n": 0}
        def real(stage):
            called["n"] += 1                                              # would be the paid call
            return "[art]"
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=real,
                             stage_cost={"video": 0.30}, ceilings={"per_run_usd": 0.0})
        with self.assertRaises(CeilingExceeded):
            run("video")
        self.assertEqual(called["n"], 0)                                  # provider NEVER called on refusal
        rows = led._dedup_rows()
        vid = [r for r in rows if r.get("step") == "video"]
        self.assertEqual(len(vid), 1)
        self.assertEqual(vid[0]["status"], "failed")                      # refusal recorded (not silent)
        self.assertIsNone(vid[0]["estimated_usd"])                        # UNPRICED — a refusal costs nothing
        self.assertEqual(led.cost_per_video("V1")["usd"], 0.0)

    def test_distinguish_refusal_from_a_real_provider_failure(self):
        # A real provider failure PROPAGATES (no false success) and is not booked as a confirmed cost.
        led = _led()
        def boom(stage):
            raise RuntimeError("provider HTTP 500")
        run = metered_runner(led, run_id="r1", video_id="V1", real_runner=boom, stage_cost={"video": 0.30})
        with self.assertRaises(RuntimeError):
            run("video")
        # nothing is confirmed; no stage is reported 'success'
        self.assertEqual(led.summary()["totals"]["confirmed_usd"], 0.0)
        self.assertFalse(any(r.get("status") == "success" for r in led._dedup_rows()))


class TestExternalIngestGuardsOff(unittest.TestCase):
    def test_awin_live_off_without_approval(self):
        r = awin_ingest.run_ingestion({"DATABASE_URL": "postgresql://x"}, approved=False,
                                      transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")

    def test_awin_live_off_in_dry_run(self):
        r = awin_ingest.run_ingestion({}, approved=True, transport=ProductionTransport())
        self.assertFalse(r["executed"])                                   # dry-run: no live affiliate call

    def test_impact_live_off_without_approval(self):
        r = impact_ingest.run_ingestion({"DATABASE_URL": "postgresql://x"}, approved=False,
                                        transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")


if __name__ == "__main__":
    unittest.main()
