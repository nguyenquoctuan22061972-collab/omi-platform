"""QA — AFFOS Revenue durable store (S5A). Offline SQLite; proves the Postgres-identical semantics.

Covers: idempotency reserve new/replay/conflict, single-logical-operation under duplicate reserves,
persistence across a simulated restart, approval expiry + revocation, row-level dedupe via
unique(source, source_record_id), and single-transaction atomicity (partial failure rolls back).
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "core"))

import revenue_store  # noqa: E402
from data_access import Repo  # noqa: E402

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def _fresh_store():
    """Store over a data_access SQLite repo (has the financial tables) + its own ingest tables."""
    repo = Repo(data_state="DRY_RUN")
    st = revenue_store.RevenueStore(repo.conn, "?")
    st.init_schema(with_commission_unique=True)
    return repo, st


class TestIdempotency(unittest.TestCase):
    def test_new_then_replay_same_body(self):
        _, st = _fresh_store()
        self.assertEqual(st.reserve("k1", "hashA")[0], "new")
        st.commit_response("k1", {"ok": True})
        state, cached = st.reserve("k1", "hashA")
        self.assertEqual(state, "replay")
        self.assertEqual(cached, {"ok": True})

    def test_conflict_different_body(self):
        _, st = _fresh_store()
        st.reserve("k1", "hashA")
        self.assertEqual(st.reserve("k1", "hashB")[0], "conflict")

    def test_single_logical_operation_under_duplicate_reserve(self):
        _, st = _fresh_store()
        results = [st.reserve("k1", "hashA")[0] for _ in range(5)]
        self.assertEqual(results.count("new"), 1)        # exactly one request "wins"
        # the rest are "pending" (reserved, not yet completed) — never a null "replay"
        self.assertTrue(all(r in ("new", "pending") for r in results))

    def test_pending_then_replay_after_complete(self):
        _, st = _fresh_store()
        self.assertEqual(st.reserve("k1", "hashA")[0], "new")      # reserved, not committed
        state, cached = st.reserve("k1", "hashA")
        self.assertEqual(state, "pending")                          # in-flight / crashed prior run
        self.assertIsNone(cached)                                   # no null response cached
        st.commit_response("k1", {"ok": 1})
        self.assertEqual(st.reserve("k1", "hashA"), ("replay", {"ok": 1}))

    def test_persistence_across_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ingest.db")
            conn = sqlite3.connect(path)
            st = revenue_store.RevenueStore(conn, "?")
            st.init_schema(with_commission_unique=False)
            st.reserve("k1", "hashA")
            st.commit_response("k1", {"ok": 1})
            st.add_approval("awin", "production",
                            (NOW - timedelta(hours=1)).isoformat(),
                            (NOW + timedelta(hours=1)).isoformat(),
                            (NOW + timedelta(hours=1)).isoformat(), "svc")
            conn.commit()
            conn.close()
            # reopen (simulated restart): history survives
            conn2 = sqlite3.connect(path)
            st2 = revenue_store.RevenueStore(conn2, "?")
            self.assertEqual(st2.reserve("k1", "hashA"), ("replay", {"ok": 1}))
            self.assertTrue(st2.is_approved("awin", "production", NOW))
            conn2.close()


class TestApprovals(unittest.TestCase):
    def test_active_within_window(self):
        _, st = _fresh_store()
        st.add_approval("awin", "production", (NOW - timedelta(hours=1)).isoformat(),
                        (NOW + timedelta(hours=1)).isoformat(),
                        (NOW + timedelta(hours=1)).isoformat(), "svc")
        self.assertTrue(st.is_approved("awin", "production", NOW))
        self.assertFalse(st.is_approved("awin", "staging", NOW))   # environment-scoped
        self.assertFalse(st.is_approved("impact", "production", NOW))  # provider-scoped

    def test_expired_blocks(self):
        _, st = _fresh_store()
        st.add_approval("awin", "production", (NOW - timedelta(hours=2)).isoformat(),
                        (NOW - timedelta(hours=1)).isoformat(),
                        (NOW - timedelta(minutes=30)).isoformat(), "svc")   # expired
        self.assertFalse(st.is_approved("awin", "production", NOW))

    def test_revoke_blocks(self):
        _, st = _fresh_store()
        rec = st.add_approval("awin", "production", (NOW - timedelta(hours=1)).isoformat(),
                              (NOW + timedelta(hours=1)).isoformat(),
                              (NOW + timedelta(hours=1)).isoformat(), "svc")
        self.assertTrue(st.is_approved("awin", "production", NOW))
        self.assertTrue(st.revoke_approval(rec["id"], "cto"))
        self.assertFalse(st.is_approved("awin", "production", NOW))
        self.assertFalse(st.revoke_approval(rec["id"], "cto"))      # already revoked -> no-op


class TestChainWriteDedupeAndAtomicity(unittest.TestCase):
    def _action(self, srid):
        return {"source": "awin", "source_record_id": srid, "tracking_link_id": "",
                "order_value": 100.0, "commission_amount": 30.0, "currency": "USD", "status": "pending"}

    def test_duplicate_source_record_id_single_commission(self):
        repo, st = _fresh_store()
        self.assertTrue(st.write_conversion_chain(self._action("T1")))
        with self.assertRaises(sqlite3.IntegrityError):
            st.write_conversion_chain(self._action("T1"))           # same action -> raises, no dup
        self.assertEqual(repo.count("commissions"), 1)

    def test_duplicate_on_skip_is_idempotent_no_raise(self):
        repo, st = _fresh_store()
        self.assertTrue(st.write_conversion_chain(self._action("T2"), on_duplicate="skip"))
        # same action with on_duplicate="skip" -> returns False, no exception, still exactly one row.
        self.assertFalse(st.write_conversion_chain(self._action("T2"), on_duplicate="skip"))
        self.assertEqual(repo.count("commissions"), 1)
        # the integrity-error tuple must carry sqlite3's error so the skip branch is reachable at all;
        # the Postgres path adds psycopg.IntegrityError (proven in the real-PG integration run).
        self.assertIn(sqlite3.IntegrityError, revenue_store._INTEGRITY_ERRORS)

    def test_partial_failure_rolls_back_whole_chain(self):
        repo, st = _fresh_store()
        # Pre-seed a commission occupying (source=awin, source_record_id=X) under a DIFFERENT id,
        # so the chain's commission insert collides on the unique index mid-transaction.
        repo.conn.execute(
            "INSERT INTO commissions (id, conversion_event_id, amount, status, source, "
            "source_record_id, data_state, currency, is_verified) VALUES "
            "('PRE-1','',10,'pending','awin','X','DRY_RUN','USD',0)")
        repo.conn.commit()
        before_clicks = repo.count("click_events")
        with self.assertRaises(sqlite3.IntegrityError):
            st.write_conversion_chain(self._action("X"))            # commission fails -> rollback all
        self.assertEqual(repo.count("click_events"), before_clicks)  # CE-X was rolled back (atomic)
        self.assertEqual(repo.query("SELECT COUNT(*) c FROM conversion_events WHERE id='CV-X'")[0]["c"], 0)


if __name__ == "__main__":
    unittest.main()
