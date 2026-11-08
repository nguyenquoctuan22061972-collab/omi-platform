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
from datetime import datetime, timezone

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


class TestCode1IdempotencyAndConfirm(unittest.TestCase):
    """CODE-1: call_id/run_id/idempotency_key, attempt/status, read-time dedup, estimated vs billed."""

    def _meta(self, conn, call_id):
        cur = conn.cursor()
        cur.execute("SELECT meta FROM audit_logs WHERE event='cost.call'")
        for (meta,) in cur.fetchall():
            m = json.loads(meta)
            if m.get("call_id") == call_id:
                return m
        return None

    def test_ids_and_default_idempotency_key(self):
        conn, led = _fresh()
        cid = led.record_call(step="script", run_id="r1", video_id="V1", usd=0.1)
        m = self._meta(conn, cid)
        self.assertEqual(m["run_id"], "r1")
        self.assertEqual(m["idempotency_key"], "r1:script:V1")   # default formula
        self.assertEqual(m["attempt"], 1)
        self.assertEqual(m["status"], "success")
        self.assertEqual(m["call_id"], cid)                       # returns the call_id

    def test_pending_then_terminal_same_call_id_counted_once(self):
        _, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="C1", status="pending")      # no cost yet
        led.record_call(step="s", video_id="V1", call_id="C1", status="success", usd=0.20, attempt=1)
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["calls"], 1)                         # pending+terminal collapse to one
        self.assertAlmostEqual(cpv["usd"], 0.20, places=6)        # terminal row's cost

    def test_duplicate_call_id_deduped_at_read(self):
        _, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="C9", status="success", usd=0.30)
        led.record_call(step="s", video_id="V1", call_id="C9", status="success", usd=0.30)  # double-log
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["calls"], 1)                         # counted once
        self.assertAlmostEqual(cpv["usd"], 0.30, places=6)        # not double-counted

    def test_skip_if_logged_best_effort(self):
        conn, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="C2", usd=0.10)
        led.record_call(step="s", video_id="V1", call_id="C2", usd=0.10, skip_if_logged=True)
        cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM audit_logs WHERE event='cost.call'")
        self.assertEqual(cur.fetchone()[0], 1)                    # second insert skipped

    def test_retry_new_call_id_counts_as_new_cost(self):
        _, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="A1", idempotency_key="k", status="failed", usd=0.05, attempt=1)
        led.record_call(step="s", video_id="V1", call_id="A2", idempotency_key="k", status="success", usd=0.07, attempt=2)
        cpv = led.cost_per_video("V1")
        self.assertEqual(cpv["calls"], 2)                         # distinct physical attempts
        self.assertAlmostEqual(cpv["usd"], 0.12, places=6)        # both real costs counted

    def test_confirm_overrides_estimate_and_split_reported(self):
        _, led = _fresh()
        led.record_call(step="voice", video_id="V1", call_id="B1", estimated_usd=0.10)   # estimate
        led.confirm_cost("B1", 0.08)                                                       # billed cheaper
        led.record_call(step="thumb", video_id="V1", call_id="B2", estimated_usd=0.05)   # estimate-only
        cpv = led.cost_per_video("V1")
        self.assertAlmostEqual(cpv["usd"], 0.13, places=6)        # 0.08 confirmed + 0.05 estimated
        self.assertAlmostEqual(cpv["confirmed_usd"], 0.08, places=6)
        self.assertAlmostEqual(cpv["estimated_only_usd"], 0.05, places=6)
        self.assertAlmostEqual(cpv["pct_confirmed"], round(0.08 / 0.13, 4), places=4)

    def test_latest_confirm_wins_by_ts(self):
        conn, led = _fresh()
        led.record_call(step="voice", video_id="V1", call_id="B1", estimated_usd=0.10)
        # two confirmations for B1 with explicit ts; the LATEST ts (0.08) must win, not the older (0.20)
        cur = conn.cursor()
        cur.execute("INSERT INTO audit_logs (id,event,actor,target,meta,ts) VALUES (?,?,?,?,?,?)",
                    ("c_old", "cost.confirm", None, "B1",
                     json.dumps({"call_id": "B1", "confirmed_billed_usd": 0.20}), "2026-01-01T00:00:00+00:00"))
        cur.execute("INSERT INTO audit_logs (id,event,actor,target,meta,ts) VALUES (?,?,?,?,?,?)",
                    ("c_new", "cost.confirm", None, "B1",
                     json.dumps({"call_id": "B1", "confirmed_billed_usd": 0.08}), "2026-02-01T00:00:00+00:00"))
        conn.commit()
        self.assertAlmostEqual(led.cost_per_video("V1")["usd"], 0.08, places=6)   # deterministic latest-by-ts

    def test_orphan_confirm_surfaced_not_counted(self):
        _, led = _fresh()
        led.record_call(step="voice", video_id="V1", call_id="B1", estimated_usd=0.10)
        led.confirm_cost("B1", 0.08)        # matched
        led.confirm_cost("GHOST", 0.50)     # orphan: no cost.call with call_id GHOST
        s = led.summary()
        self.assertEqual(s["orphan_confirms"]["count"], 1)
        self.assertIn("GHOST", s["orphan_confirms"]["call_ids"])
        self.assertAlmostEqual(s["orphan_confirms"]["usd"], 0.50, places=6)
        self.assertAlmostEqual(s["per_video"]["V1"]["usd"], 0.08, places=6)        # orphan NOT added to cost

    def test_confirm_row_is_insert_only_separate_event(self):
        conn, led = _fresh()
        led.record_call(step="voice", video_id="V1", call_id="B9", estimated_usd=0.10)
        led.confirm_cost("B9", 0.09)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM audit_logs WHERE event='cost.confirm'")
        self.assertEqual(cur.fetchone()[0], 1)                    # confirmation is a separate appended row
        cur.execute("SELECT COUNT(*) FROM audit_logs WHERE event='cost.call'")
        self.assertEqual(cur.fetchone()[0], 1)                    # original call row untouched (no UPDATE)


class TestG1EqualTsTiebreak(unittest.TestCase):
    """G1: ORDER BY ts, id — stable, deterministic winner even when confirmation timestamps are equal."""

    def _confirm_row(self, conn, rid, call_id, usd, ts):
        conn.cursor().execute(
            "INSERT INTO audit_logs (id,event,actor,target,meta,ts) VALUES (?,?,?,?,?,?)",
            (rid, "cost.confirm", None, call_id,
             json.dumps({"call_id": call_id, "confirmed_billed_usd": usd}), ts))
        conn.commit()

    def test_equal_ts_tiebreak_is_stable_and_deterministic(self):
        conn, led = _fresh()
        led.record_call(step="voice", video_id="V1", call_id="B1", estimated_usd=0.10)
        TS = "2026-01-01T00:00:00+00:00"                 # identical timestamps
        self._confirm_row(conn, "id_a", "B1", 0.20, TS)  # id_a < id_b lexically
        self._confirm_row(conn, "id_b", "B1", 0.08, TS)
        r1 = led.cost_per_video("V1")["usd"]
        r2 = led.cost_per_video("V1")["usd"]
        self.assertEqual(r1, r2)                          # stable across reads
        self.assertAlmostEqual(r1, 0.08, places=6)        # ORDER BY ts,id -> id_b last -> 0.08 wins


class TestG2StalePending(unittest.TestCase):
    """G2: read-only stale-pending diagnostics in summary() — count, age, configurable threshold."""

    def _pending_row(self, conn, rid, call_id, ts, estimated=None):
        meta = {"call_id": call_id, "status": "pending", "video_id": "V1", "estimated_usd": estimated,
                "usd": estimated}
        conn.cursor().execute(
            "INSERT INTO audit_logs (id,event,actor,target,meta,ts) VALUES (?,?,?,?,?,?)",
            (rid, "cost.call", None, "V1", json.dumps(meta), ts))
        conn.commit()

    def test_pending_without_terminal_surfaced(self):
        _, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="P1", status="pending", estimated_usd=0.05)
        self.assertEqual(led.summary()["pending"]["count"], 1)

    def test_pending_resolved_by_terminal_not_counted(self):
        _, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="P1", status="pending")
        led.record_call(step="s", video_id="V1", call_id="P1", status="success", estimated_usd=0.05)
        self.assertEqual(led.summary()["pending"]["count"], 0)

    def test_stale_threshold_configurable(self):
        conn, led = _fresh()
        self._pending_row(conn, "p_old", "P1", "2026-01-01T00:00:00+00:00")
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)                  # 1 day (86400s) later
        self.assertEqual(led.summary(now=now, stale_after_seconds=3600)["pending"]["stale_count"], 1)
        self.assertEqual(led.summary(now=now, stale_after_seconds=10 * 86400)["pending"]["stale_count"], 0)
        s = led.summary(now=now, stale_after_seconds=3600)
        self.assertAlmostEqual(s["pending"]["oldest_age_seconds"], 86400.0, places=0)
        self.assertIn("P1", s["pending"]["stale_call_ids"])

    def test_pending_unpriced_cost_not_assumed_zero(self):
        _, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="P1", status="pending")   # no estimate
        s = led.summary()
        self.assertEqual(s["pending"]["unpriced_count"], 1)
        self.assertEqual(s["per_video"]["V1"]["usd_unpriced_calls"], 1)            # flagged, not 0-cost
        self.assertEqual(s["per_video"]["V1"]["usd_priced_calls"], 0)

    def test_legacy_without_status_not_pending(self):
        conn, led = _fresh()
        # legacy pre-CODE-1 row: meta has usd but NO status / call_id
        conn.cursor().execute(
            "INSERT INTO audit_logs (id,event,actor,target,meta,ts) VALUES (?,?,?,?,?,?)",
            ("leg1", "cost.call", None, "V1",
             json.dumps({"video_id": "V1", "usd": 0.10}), "2026-01-01T00:00:00+00:00"))
        conn.commit()
        s = led.summary()
        self.assertEqual(s["pending"]["count"], 0)                       # legacy (no status) NOT pending
        self.assertAlmostEqual(s["per_video"]["V1"]["usd"], 0.10, places=6)  # still aggregates (back-compat)

    def test_summary_is_read_only_no_write(self):
        conn, led = _fresh()
        led.record_call(step="s", video_id="V1", call_id="P1", status="pending")
        cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM audit_logs"); before = cur.fetchone()[0]
        led.summary(stale_after_seconds=1)                 # even flagging stale must not write/mark failed
        cur.execute("SELECT COUNT(*) FROM audit_logs"); after = cur.fetchone()[0]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
