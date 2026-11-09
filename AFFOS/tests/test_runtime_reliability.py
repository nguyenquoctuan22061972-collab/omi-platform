"""QA — AFFOS runtime reliability (Milestone 2, TASK 2): Postgres connect-retry, mid-life reconnect,
and the liveness (/health) vs readiness (/ready) split. Offline — a FAKE `psycopg` module stands in for
a real DB (no network, no cost). The equivalent against real Postgres 16 is in the staging verify suite.

Proves:
  * connect retry (opt-in via AFFOS_DB_CONNECT_ATTEMPTS) succeeds after transient failures,
  * retry exhaustion raises StoreUnavailable and NEVER downgrades to SQLite while a DB is configured,
  * a store whose connection DIES mid-process is reconnected (probe=True), not served dead,
  * readiness returns 503 when Postgres is unreachable and 200 once it recovers (disconnect -> recover),
  * liveness (/health) stays 200 and never touches the DB.
"""
import importlib.machinery
import json
import os
import sys
import threading
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import server  # noqa: E402


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, q):
        if self.conn.broken:
            raise RuntimeError("server closed the connection unexpectedly")   # a real driver error
        self.conn.executed.append(q)

    def fetchone(self):
        return (1,)

    def close(self):
        pass


class _FakeConn:
    """Minimal psycopg-like connection whose liveness we can toggle via `broken`."""
    def __init__(self):
        self.broken = False
        self.closed = 0
        self.executed = []

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        pass


class _ReliabilityBase(unittest.TestCase):
    def setUp(self):
        self._saved = (server._STORE, server._STORE_BUILT)
        server._STORE, server._STORE_BUILT = None, False
        self._psycopg_saved = sys.modules.get("psycopg")
        self._env_keys = ("DATABASE_URL", "SUPABASE_DB_URL", "AFFOS_INGEST_DB",
                          "AFFOS_DB_CONNECT_ATTEMPTS", "AFFOS_DB_CONNECT_BACKOFF_MS")
        self._env_saved = {k: os.environ.get(k) for k in self._env_keys}
        for k in self._env_keys:
            os.environ.pop(k, None)

    def tearDown(self):
        server._STORE, server._STORE_BUILT = self._saved
        if self._psycopg_saved is not None:
            sys.modules["psycopg"] = self._psycopg_saved
        else:
            sys.modules.pop("psycopg", None)
        for k, v in self._env_saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _install_fake_psycopg(self, connect):
        mod = types.ModuleType("psycopg")
        mod.__spec__ = importlib.machinery.ModuleSpec("psycopg", loader=None)   # so find_spec() works
        mod.connect = connect

        class _IntegrityError(Exception):
            pass

        mod.IntegrityError = _IntegrityError
        sys.modules["psycopg"] = mod


class TestConnectRetry(_ReliabilityBase):
    def test_retry_succeeds_after_transient_failures(self):
        os.environ["DATABASE_URL"] = "postgresql://unreachable/db"
        os.environ["AFFOS_DB_CONNECT_ATTEMPTS"] = "3"
        os.environ["AFFOS_DB_CONNECT_BACKOFF_MS"] = "0"      # no real delay in tests
        n = {"c": 0}

        def flaky(url):
            n["c"] += 1
            if n["c"] < 3:
                raise OSError("connection refused")           # fails attempts 1 and 2
            return _FakeConn()                                # attempt 3 succeeds

        self._install_fake_psycopg(flaky)
        st = server._get_store()
        self.assertIsNotNone(st)
        self.assertTrue(server._STORE_BUILT)
        self.assertEqual(n["c"], 3)                           # retried within ONE _get_store() call

    def test_retry_exhausted_raises_and_no_sqlite_downgrade(self):
        os.environ["DATABASE_URL"] = "postgresql://unreachable/db"
        os.environ["AFFOS_INGEST_DB"] = ":memory:"            # present but MUST NOT be used while DB set
        os.environ["AFFOS_DB_CONNECT_ATTEMPTS"] = "3"
        n = {"c": 0}

        def always_down(url):
            n["c"] += 1
            raise OSError("connection refused")

        self._install_fake_psycopg(always_down)
        with self.assertRaises(server.StoreUnavailable):
            server._get_store()
        self.assertEqual(n["c"], 3)                           # all attempts used
        self.assertFalse(server._STORE_BUILT)
        self.assertIsNone(server._STORE)                      # NO silent SQLite fallback


class TestMidLifeReconnect(_ReliabilityBase):
    def test_dead_connection_is_reconnected_on_probe(self):
        os.environ["DATABASE_URL"] = "postgresql://host/db"
        conns = []

        def connect(url):
            c = _FakeConn()
            conns.append(c)
            return c

        self._install_fake_psycopg(connect)
        st1 = server._get_store()                             # build with conn #1
        self.assertIs(st1.conn, conns[0])
        # hot path (probe=False) keeps serving the SAME store even if the connection later dies
        conns[0].broken = True
        self.assertIs(server._get_store(), st1)               # no probe -> no churn
        # the request/readiness path probes and RECONNECTS the dead connection
        st2 = server._get_store(probe=True)
        self.assertIsNot(st2, st1)
        self.assertIs(st2.conn, conns[1])                     # a fresh connection was built
        self.assertEqual(len(conns), 2)
        self.assertFalse(st2.conn.broken)


class TestLivenessVsReadiness(_ReliabilityBase):
    def test_liveness_never_touches_db(self):
        os.environ["DATABASE_URL"] = "postgresql://host/db"

        def explode(url):
            raise AssertionError("/health must NOT open a DB connection")

        self._install_fake_psycopg(explode)
        code, body = server.build_health_response()
        self.assertEqual(code, 200)                           # liveness green regardless of DB
        self.assertEqual(json.loads(body)["service"], "affos-runtime")

    def test_readiness_200_when_no_db_configured(self):
        code, body = server.build_ready_response()
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["ready"])

    def test_readiness_503_when_db_down_then_200_after_recovery(self):
        os.environ["DATABASE_URL"] = "postgresql://host/db"
        state = {"up": False, "conns": []}

        def connect(url):
            if not state["up"]:
                raise OSError("connection refused")
            c = _FakeConn()
            state["conns"].append(c)
            return c

        self._install_fake_psycopg(connect)
        # DB down -> readiness 503 (no false success), store not built
        code, _ = server.build_ready_response()
        self.assertEqual(code, 503)
        self.assertFalse(server._STORE_BUILT)
        # DB recovers -> readiness probes, builds, and reports 200
        state["up"] = True
        code, body = server.build_ready_response()
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["ready"])

    def test_readiness_reconnects_a_connection_that_died(self):
        os.environ["DATABASE_URL"] = "postgresql://host/db"
        conns = []

        def connect(url):
            c = _FakeConn()
            conns.append(c)
            return c

        self._install_fake_psycopg(connect)
        self.assertEqual(server.build_ready_response()[0], 200)   # built + alive
        conns[0].broken = True                                    # connection dies mid-life
        self.assertEqual(server.build_ready_response()[0], 200)   # readiness reconnects -> still 200
        self.assertEqual(len(conns), 2)                           # proof it rebuilt, not served dead


class TestConcurrencyNoReconnectStorm(_ReliabilityBase):
    def test_many_threads_detect_outage_cause_one_reconnect(self):
        os.environ["DATABASE_URL"] = "postgresql://host/db"
        lock = threading.Lock()
        conns = []

        def connect(url):
            with lock:
                c = _FakeConn()
                conns.append(c)
                return c

        self._install_fake_psycopg(connect)
        server._get_store()                               # initial build -> conn #1
        self.assertEqual(len(conns), 1)
        conns[0].broken = True                            # the live connection dies

        n = 16
        barrier = threading.Barrier(n)
        got = []

        def worker():
            barrier.wait()                                # maximize contention on the dead connection
            got.append(server._get_store(probe=True))

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(conns), 2)                   # exactly ONE reconnect, not a storm
        self.assertTrue(all(s is got[0] for s in got))    # every thread sees the same rebuilt store
        self.assertIs(got[0].conn, conns[1])
        self.assertFalse(got[0].conn.broken)


class TestTimeoutHandling(_ReliabilityBase):
    def test_connect_timeout_is_retried_then_raises(self):
        os.environ["DATABASE_URL"] = "postgresql://host/db?connect_timeout=1"
        os.environ["AFFOS_DB_CONNECT_ATTEMPTS"] = "3"
        n = {"c": 0}

        def times_out(url):
            n["c"] += 1
            raise TimeoutError("connect timed out")       # DB not responding at connect

        self._install_fake_psycopg(times_out)
        with self.assertRaises(server.StoreUnavailable):  # a timeout is a connect failure -> StoreUnavailable
            server._get_store()
        self.assertEqual(n["c"], 3)                       # retried the configured number of times
        self.assertFalse(server._STORE_BUILT)


class TestRetryIsConnectScoped(_ReliabilityBase):
    def test_retry_does_not_fire_on_a_successful_connect(self):
        # Retry/backoff is scoped to establishing the CONNECTION, never a blanket write retry (so it can
        # never re-issue a non-idempotent write). A connect that succeeds first-try is called exactly once
        # even with attempts=3, and the store's write path is reached without any retry wrapper.
        os.environ["DATABASE_URL"] = "postgresql://host/db"
        os.environ["AFFOS_DB_CONNECT_ATTEMPTS"] = "3"
        n = {"c": 0}

        def connect(url):
            n["c"] += 1
            return _FakeConn()

        self._install_fake_psycopg(connect)
        st = server._get_store()
        self.assertEqual(n["c"], 1)                        # no extra connects on success
        # a write goes straight through (no retry loop around the store operation)
        st.conn.cursor().execute("INSERT INTO audit_logs DEFAULT VALUES")
        self.assertEqual(n["c"], 1)                        # unchanged — writes are not retried by the runtime


if __name__ == "__main__":
    unittest.main()
