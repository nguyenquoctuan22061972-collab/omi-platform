"""QA — AFFOS provider-adapter framework (COST-1). Offline; FAKE transport -> ZERO network / ZERO cost.

Proves: credential-by-name + auth header; request shape; response parse -> ProviderResult (artifact,
billed_usd, usage); non-2xx -> error; unconfigured endpoint refuses; missing credential refuses (no call);
and end-to-end wiring into provider_runner + baseline (all with a fake transport).
"""
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT, "..", "apps", "content-factory", "pipeline")))

import cost_ledger            # noqa: E402
from provider_runner import ProviderResult, ProviderRunner, CREDENTIAL_ENV, reconcile_billed  # noqa: E402
from provider_adapters import (ProviderSpec, make_adapter, build_adapters, reference_specs,  # noqa: E402
                               AdapterNotConfigured)
from baseline_runner import run_baseline, build_report, default_topics  # noqa: E402
from pipeline import ContentPipeline  # noqa: E402

CREDS = {v: "SECRET" for v in CREDENTIAL_ENV.values()}


class FakeTransport:
    """Records the last request and returns a canned (status, json)."""
    def __init__(self, status=200, resp=None):
        self.status, self.resp, self.calls = status, (resp or {}), []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": body})
        return self.status, self.resp


class TestAdapterFramework(unittest.TestCase):
    def _spec(self):
        return ProviderSpec(endpoint="https://api.test/elevenlabs", auth_header="xi-api-key", auth_prefix="",
                            build_body=lambda topic, stage: {"topic": topic, "stage": stage})

    def test_builds_request_and_parses_result(self):
        ft = FakeTransport(200, {"artifact": "AUDIO_URL", "cost_usd": 0.30, "usage": {"chars": 1200}})
        adapter = make_adapter("elevenlabs", self._spec(), transport=ft, env=CREDS)
        res = adapter("AI topic", "video")
        self.assertIsInstance(res, ProviderResult)
        self.assertEqual(res.artifact, "AUDIO_URL")
        self.assertAlmostEqual(res.billed_usd, 0.30, places=6)
        self.assertEqual(res.usage, {"chars": 1200})
        call = ft.calls[0]
        self.assertEqual(call["url"], "https://api.test/elevenlabs")
        self.assertEqual(call["headers"]["xi-api-key"], "SECRET")          # credential placed in the auth header
        self.assertEqual(call["body"], {"topic": "AI topic", "stage": "video"})

    def test_missing_credential_refuses_without_calling(self):
        ft = FakeTransport()
        adapter = make_adapter("elevenlabs", self._spec(), transport=ft, env={})   # no creds
        with self.assertRaises(RuntimeError):
            adapter("t", "video")
        self.assertEqual(ft.calls, [])                                    # never called the transport

    def test_non_2xx_is_error(self):
        ft = FakeTransport(500, {})
        adapter = make_adapter("elevenlabs", self._spec(), transport=ft, env=CREDS)
        with self.assertRaises(RuntimeError):
            adapter("t", "video")

    def test_unconfigured_endpoint_refuses(self):
        ft = FakeTransport()
        adapter = make_adapter("model", reference_specs()["model"], transport=ft, env=CREDS)  # endpoint=""
        with self.assertRaises(AdapterNotConfigured):
            adapter("t", "script")
        self.assertEqual(ft.calls, [])

    def test_bearer_prefix_applied(self):
        ft = FakeTransport(200, {"artifact": "X", "cost_usd": 0.02})
        spec = ProviderSpec(endpoint="https://api.test/model", auth_header="Authorization", auth_prefix="Bearer ")
        make_adapter("model", spec, transport=ft, env=CREDS)("t", "script")
        self.assertEqual(ft.calls[0]["headers"]["Authorization"], "Bearer SECRET")


class TestWiredIntoRunnerAndBaseline(unittest.TestCase):
    def test_full_flow_with_fake_transport(self):
        # configured specs for all paid providers, all pointing at the fake transport (no network)
        specs = {p: ProviderSpec(endpoint=f"https://api.test/{p}",
                                 build_body=lambda topic, stage: {"t": topic, "s": stage},
                                 parse=(lambda price: (lambda resp: ProviderResult(
                                     artifact=resp["artifact"], billed_usd=price, usage={})))(price))
                 for p, price in {"model": 0.02, "canva": 0.05, "elevenlabs": 0.30, "vidiq": 0.00}.items()}
        ft = FakeTransport(200, {"artifact": "OK"})
        adapters = build_adapters(specs, transport=ft, env=CREDS)
        conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
        led = cost_ledger.CostLedger(conn, "?"); led.init_schema()
        sink = []
        pr = ProviderRunner(adapters, live=True, env=CREDS, usage_sink=sink)
        topics = default_topics(2)
        results = run_baseline(led, topics=topics, real_runner_factory=pr.factory(),
                               pipeline_factory=ContentPipeline,
                               stage_cost={"script": 0.02, "thumbnail": 0.05, "video": 0.30},
                               ceilings={"per_baseline_usd": 100.0})
        reconcile_billed(led, sink, topics)
        rep = build_report(led, results)
        self.assertGreater(rep["pct_confirmed"], 0.0)
        self.assertAlmostEqual(rep["totals"]["confirmed_usd"], 2 * (0.02 + 0.05 + 0.30 + 0.00), places=6)
        self.assertTrue(len(ft.calls) >= 2 * 4)                          # fake transport used for paid stages


if __name__ == "__main__":
    unittest.main()
