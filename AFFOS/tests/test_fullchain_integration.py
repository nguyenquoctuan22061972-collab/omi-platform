"""QA — AFFOS COST-1 FULL-CHAIN integration (Milestone 1). Offline; every provider call goes through an
INJECTED fake transport -> ZERO network / ZERO cost.

Exercises the WHOLE chain together (not module-by-module):
    provider_adapters -> provider_runner -> pilot_metering (metered_runner) -> cost_ledger
                      -> ContentPipeline -> audit_logs rows -> baseline report

Scenarios (CTO Milestone-1 VI):
  1. success (mock provider) through the real ContentPipeline + cost confirmation via reconcile_billed,
  2. provider ERROR (non-2xx) -> RuntimeError propagates, NO false success, NO confirmation,
  3. provider TIMEOUT -> propagates, NO false success,
  4. retry re-bill -> two DISTINCT attempt call_ids, both counted (no missing cost),
  5. ceiling exceeded -> refused BEFORE the provider call, recorded (not silent), run not done,
  6. dry-run (live=False) -> provider is NEVER called,
  7. cost confirmation -> reconcile overrides estimates -> pct_confirmed > 0,
  8. database UNAVAILABLE -> no false success AND no provider call we could not account for.
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, "..", "apps", "content-factory", "pipeline")))

import cost_ledger            # noqa: E402
from provider_runner import (ProviderRunner, ProviderResult, CREDENTIAL_ENV,  # noqa: E402
                             reconcile_billed, ProvidersDisabled)
from provider_adapters import ProviderSpec, build_adapters  # noqa: E402
from pilot_metering import metered_runner, confirm_stage, CeilingExceeded  # noqa: E402
from baseline_runner import run_baseline, build_report, default_topics  # noqa: E402
from pipeline import ContentPipeline  # noqa: E402

CREDS = {v: "SECRET" for v in CREDENTIAL_ENV.values()}
PRICES = {"model": 0.02, "canva": 0.05, "elevenlabs": 0.30, "vidiq": 0.00}   # paid providers (billed_usd)
STAGE_COST = {"script": 0.02, "thumbnail": 0.05, "video": 0.30}              # pilot estimate basis


class _Transport:
    """Base fake transport: records every call. Subclasses decide the response / failure."""
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "stage": (body or {}).get("s")})
        return self._respond()

    def _respond(self):
        return 200, {"artifact": "OK"}


class OKTransport(_Transport):
    pass


class ErrTransport(_Transport):
    def _respond(self):
        return 500, {}                     # non-2xx -> adapter raises RuntimeError


class TimeoutTransport(_Transport):
    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "stage": (body or {}).get("s")})
        raise TimeoutError("provider timed out")


def _led():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?")
    led.init_schema()
    return led


def _specs():
    # endpoint configured (so the adapter does NOT refuse); parse returns the per-provider billed price.
    return {p: ProviderSpec(endpoint=f"https://api.test/{p}",
                            build_body=lambda topic, stage: {"t": topic, "s": stage},
                            parse=(lambda price: (lambda resp: ProviderResult(
                                artifact=resp.get("artifact", "OK"), billed_usd=price, usage={})))(PRICES[p]))
            for p in PRICES}


def _wire(led, transport, *, live=True, ceilings=None, stage_cost=None, usage_sink=None,
          run_id="r1", video_id="V1"):
    """Build the real wired runner: adapters(fake transport) -> ProviderRunner -> metered_runner(ledger)."""
    adapters = build_adapters(_specs(), transport=transport, env=CREDS)
    pr = ProviderRunner(adapters, live=live, env=CREDS, usage_sink=usage_sink)
    return metered_runner(led, run_id=run_id, video_id=video_id, job_id="wf",
                          real_runner=pr.factory()(f"topic-{run_id}"),
                          stage_cost=stage_cost or STAGE_COST, ceilings=ceilings)


class TestFullChainSuccess(unittest.TestCase):
    def test_success_then_confirm(self):
        led = _led(); ft = OKTransport(); sink = []
        runner = _wire(led, ft, usage_sink=sink)
        out = ContentPipeline("AI Automation").run_all(runner=runner)
        self.assertTrue(out["done"])
        # 4 paid providers actually called through the chain (script/thumbnail/video/publish)
        self.assertEqual(len(ft.calls), 4)
        self.assertEqual(sorted(c["stage"] for c in ft.calls), ["publish", "script", "thumbnail", "video"])
        # before reconcile: estimates only
        self.assertEqual(led.summary()["totals"]["pct_confirmed"], 0.0)
        reconcile_billed(led, sink, [f"topic-r1"])
        t = led.summary()["totals"]
        self.assertAlmostEqual(t["confirmed_usd"], 0.02 + 0.05 + 0.30 + 0.00, places=6)
        self.assertEqual(t["pct_confirmed"], 1.0)


class TestFullChainProviderError(unittest.TestCase):
    def test_non_2xx_propagates_no_false_success(self):
        led = _led(); ft = ErrTransport()
        p = ContentPipeline("AI Automation")
        with self.assertRaises(RuntimeError):
            p.run_all(runner=_wire(led, ft))
        self.assertFalse(p.is_done())                       # no false success
        self.assertEqual(len(ft.calls), 1)                  # only the first paid stage (script) was attempted
        rows = {r["step"]: r["status"] for r in led._dedup_rows() if r.get("step")}
        self.assertEqual(rows.get("script"), "failed")      # crashed attempt classified failed (not pending)
        self.assertEqual(led.summary()["totals"]["confirmed_usd"], 0.0)   # nothing confirmed


class TestFullChainTimeout(unittest.TestCase):
    def test_timeout_propagates_no_false_success(self):
        led = _led(); ft = TimeoutTransport()
        p = ContentPipeline("AI Automation")
        with self.assertRaises(TimeoutError):
            p.run_all(runner=_wire(led, ft))
        self.assertFalse(p.is_done())
        self.assertEqual(led.summary()["totals"]["confirmed_usd"], 0.0)
        # the failed attempt is surfaced, not silently dropped
        self.assertEqual(sum(1 for r in led._dedup_rows() if r.get("status") == "failed"), 1)


class TestRetryReBillCounted(unittest.TestCase):
    def test_two_attempts_two_call_ids_no_missing_cost(self):
        led = _led()
        n = {"v": 0}
        def flaky(stage):
            n["v"] += 1
            if n["v"] == 1:
                raise RuntimeError("transient provider 500")
            return f"[ok:{stage}]"
        runner = metered_runner(led, run_id="r1", video_id="V1", real_runner=flaky,
                                stage_cost={"video": 0.30})
        with self.assertRaises(RuntimeError):
            runner("video")                                 # attempt 1 fails
        self.assertEqual(runner("video"), "[ok:video]")     # attempt 2 (retry) succeeds
        vids = {r["call_id"]: r["status"] for r in led._dedup_rows() if r.get("step") == "video"}
        self.assertEqual(sorted(vids), ["r1:video#1", "r1:video#2"])   # distinct attempts, not collapsed
        self.assertEqual(vids["r1:video#1"], "failed")
        self.assertEqual(vids["r1:video#2"], "success")
        # confirm each attempt's REAL bill separately -> both counted (no missing cost on retry)
        confirm_stage(led, "r1", "video", 0.26, attempt=1)
        confirm_stage(led, "r1", "video", 0.28, attempt=2)
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["calls"], 2)
        self.assertAlmostEqual(cpv["confirmed_usd"], 0.54, places=6)


class TestCeilingStopsBeforePaidCall(unittest.TestCase):
    def test_per_run_ceiling_refuses_before_provider(self):
        led = _led(); ft = OKTransport()
        runner = _wire(led, ft, ceilings={"per_run_usd": 0.05})   # script 0.02 ok; thumbnail would reach 0.07
        p = ContentPipeline("AI Automation")
        with self.assertRaises(CeilingExceeded):
            p.run_all(runner=runner)
        self.assertFalse(p.is_done())
        self.assertEqual(len(ft.calls), 1)                  # only script hit the provider; thumbnail refused first
        self.assertEqual([c["stage"] for c in ft.calls], ["script"])
        rows = {r["step"]: r["status"] for r in led._dedup_rows() if r.get("step")}
        self.assertEqual(rows.get("thumbnail"), "failed")   # refusal recorded, not silent
        self.assertAlmostEqual(led.cost_per_video("V1")["usd"], 0.02, places=6)   # refused stage adds no cost


class TestDryRunNeverCallsProvider(unittest.TestCase):
    def test_not_live_means_zero_provider_calls(self):
        led = _led(); ft = OKTransport()
        runner = _wire(led, ft, live=False)                 # provider_runner gate: not live
        p = ContentPipeline("AI Automation")
        with self.assertRaises(ProvidersDisabled):
            p.run_all(runner=runner)
        self.assertEqual(ft.calls, [])                      # NO provider HTTP call in dry-run
        self.assertFalse(p.is_done())


class _DownLedger:
    """Simulates the cost ledger's DB being unavailable: every write raises (like a psycopg OperationalError)."""
    def record_call(self, **kw):
        raise RuntimeError("database unavailable (OperationalError)")


class TestDatabaseUnavailableNoFalseSuccess(unittest.TestCase):
    def test_db_down_blocks_run_and_paid_call(self):
        ft = OKTransport()
        # metered_runner logs the 'pending' cost.call BEFORE the provider call; if that write fails (DB down),
        # the run must raise and the provider must never be called (no spend we cannot account for).
        runner = _wire(_DownLedger(), ft)
        p = ContentPipeline("AI Automation")
        with self.assertRaises(RuntimeError):
            p.run_all(runner=runner)
        self.assertFalse(p.is_done())                       # no false success when the DB is unavailable
        self.assertEqual(ft.calls, [])                      # and no paid provider call was made


if __name__ == "__main__":
    unittest.main()
