"""QA — AFFOS Token/Cost Ledger (Phase 0, additive). Offline SQLite; proves the Postgres-identical semantics.

Covers: writing cost.call rows to the EXISTING audit_logs shape, per-video and per-workflow roll-ups,
token sums, cache_hit/deduped counters, usd computed from unit price, and the honesty rule — usd stays
None when no price basis exists and unpriced calls are reported separately (total never silently low).
"""
import json
import os
import sqlite3
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import cost_ledger  # noqa: E402


def _fresh():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    led = cost_ledger.CostLedger(conn, "?")
    led.init_schema()
    return conn, led


class TestWriteAndRollup(unittest.TestCase):
    def test_cost_per_video_sums_priced_calls(self):
        _, led = _fresh()
        led.record_call(step="script", model="m", in_tokens=1000, out_tokens=500,
                        unit_cost_in=0.000002, unit_cost_out=0.000006, job_id="J1", video_id="V1")
        led.record_call(step="voice", model="eleven", usd=0.30, job_id="J1", video_id="V1")
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["calls"], 2)
        self.assertEqual(cpv["in_tokens"], 1000)
        self.assertEqual(cpv["out_tokens"], 500)
        # 1000*2e-6 + 500*6e-6 = 0.002 + 0.003 = 0.005 ; + 0.30 = 0.305
        self.assertAlmostEqual(cpv["usd"], 0.305, places=6)
        self.assertEqual(cpv["usd_unpriced_calls"], 0)

    def test_cost_per_workflow_groups_by_job(self):
        _, led = _fresh()
        led.record_call(step="a", usd=0.10, job_id="J1", video_id="V1")
        led.record_call(step="b", usd=0.20, job_id="J1", video_id="V2")
        led.record_call(step="c", usd=0.05, job_id="J2", video_id="V3")
        self.assertAlmostEqual(led.cost_per_workflow("J1")["usd"], 0.30, places=6)
        self.assertEqual(led.cost_per_workflow("J1")["calls"], 2)
        self.assertAlmostEqual(led.cost_per_workflow("J2")["usd"], 0.05, places=6)

    def test_unpriced_call_keeps_usd_none_and_is_reported(self):
        _, led = _fresh()
        led.record_call(step="research", in_tokens=100, out_tokens=0, job_id="J1", video_id="V1")  # no price
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["usd"], 0.0)                 # nothing fabricated
        self.assertEqual(cpv["usd_priced_calls"], 0)
        self.assertEqual(cpv["usd_unpriced_calls"], 1)    # flagged: total is NOT complete
        self.assertEqual(cpv["in_tokens"], 100)

    def test_cache_hit_and_dedup_counters(self):
        _, led = _fresh()
        led.record_call(step="x", usd=0.0, video_id="V1", cache_hit=True)
        led.record_call(step="y", usd=0.0, video_id="V1", deduped=True)
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["cache_hits"], 1)
        self.assertEqual(cpv["deduped"], 1)

    def test_row_written_to_audit_logs_as_cost_event(self):
        conn, led = _fresh()
        led.record_call(step="script", usd=0.1, video_id="V1", actor="n8n")
        cur = conn.cursor()
        cur.execute("SELECT event, actor, target, meta FROM audit_logs")
        row = cur.fetchone()
        self.assertEqual(row["event"], "cost.call")       # reuses audit_logs, no new table
        self.assertEqual(row["actor"], "n8n")
        self.assertEqual(row["target"], "V1")             # target = video_id for grouping without parsing meta
        self.assertEqual(json.loads(row["meta"])["step"], "script")

    def test_summary_shape(self):
        _, led = _fresh()
        led.record_call(step="a", usd=0.10, job_id="J1", video_id="V1")
        led.record_call(step="b", usd=0.20, job_id="J1", video_id="V2")
        s = led.summary()
        self.assertAlmostEqual(s["totals"]["usd"], 0.30, places=6)
        self.assertIn("V1", s["per_video"])
        self.assertIn("J1", s["per_workflow"])
        self.assertEqual(s["per_workflow"]["J1"]["calls"], 2)


if __name__ == "__main__":
    unittest.main()
