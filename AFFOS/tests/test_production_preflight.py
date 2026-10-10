"""QA — Production preflight gate logic (no network, no subprocess)."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "ops"))
import production_preflight as pf   # noqa: E402


class TestProductionPreflight(unittest.TestCase):
    def test_credentials_present_missing(self):
        self.assertEqual(pf.gate_credentials({})["status"], "MISSING")
        g = pf.gate_credentials({"AWIN_API_TOKEN": "x", "AWIN_PUBLISHER_ID": "5"})
        self.assertEqual(g["status"], "PRESENT")

    def test_code_gates_pass(self):
        self.assertEqual(pf.gate_connector_interface()["status"], "PASS")
        self.assertEqual(pf.gate_awin_adapter({})["status"], "PASS")
        self.assertEqual(pf.gate_secret_scan()["status"], "PASS")

    def test_pg_gates_fail_without_url(self):
        self.assertEqual(pf.gate_pg_connect({})["status"], "FAIL")
        self.assertEqual(pf.gate_pg_write({})["status"], "FAIL")


class _FakeCursor:
    def __init__(self, conn): self.conn = conn; self._rows = []
    def execute(self, sql, params=()):
        s = sql.strip().upper()
        if s.startswith("CREATE TEMP TABLE"):
            if self.conn.fail_on_create: raise RuntimeError("create failed")
            self.conn.temp_exists_uncommitted = True
        elif s.startswith("INSERT"):
            if self.conn.fail_on_insert: raise RuntimeError("insert failed")
            self.conn.temp_rows += 1
        elif s.startswith("SELECT COUNT(*) FROM _AFFOS_PF"):
            # table visible only while it exists (uncommitted temp, or if rollback didn't discard)
            if not self.conn.temp_exists_uncommitted:
                raise RuntimeError('relation "_affos_pf" does not exist')
            self._rows = [(self.conn.temp_rows,)]
        else:
            self._rows = [(1,)]
    def fetchone(self): return self._rows[0] if self._rows else (0,)


class _FakeConn:
    """Models a transactional connection: rollback discards the temp table unless configured not to."""
    def __init__(self, fail_on_create=False, fail_on_insert=False,
                 fail_on_rollback=False, rollback_discards=True):
        self.autocommit = True
        self.fail_on_create = fail_on_create
        self.fail_on_insert = fail_on_insert
        self.fail_on_rollback = fail_on_rollback
        self.rollback_discards = rollback_discards
        self.temp_exists_uncommitted = False
        self.temp_rows = 0
    def cursor(self): return _FakeCursor(self)
    def rollback(self):
        if self.fail_on_rollback: raise RuntimeError("rollback failed")
        if self.rollback_discards: self.temp_exists_uncommitted = False
    def close(self): pass


class TestPgWriteGate(unittest.TestCase):
    def test_success_rollback_verified(self):
        c = _FakeConn()
        r = pf.gate_pg_write({}, _conn=c)
        self.assertEqual(r["status"], "PASS")
        self.assertIn("rollback verified", r["detail"])
        self.assertFalse(c.autocommit)          # forced into a transaction

    def test_write_error_fails(self):
        r = pf.gate_pg_write({}, _conn=_FakeConn(fail_on_insert=True))
        self.assertEqual(r["status"], "FAIL")

    def test_rollback_did_not_discard_fails(self):
        # rollback ran but the row/table survived → must NOT be reported as rolled back
        r = pf.gate_pg_write({}, _conn=_FakeConn(rollback_discards=False))
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("rollback not verified", r["detail"])

    def test_rollback_error_fails(self):
        r = pf.gate_pg_write({}, _conn=_FakeConn(fail_on_rollback=True))
        self.assertEqual(r["status"], "FAIL")   # rollback error is never swallowed

    def test_not_ready_without_external_deps(self):
        out = pf.run({}, run_tests=False, probe_network=False)
        self.assertFalse(out["ready_for_live_call"])   # external deps missing → never ready
        names = {g["gate"] for g in out["gates"]}
        self.assertEqual(len(names), 8)                # exactly 8 gates reported

    def test_credentials_never_leak_value(self):
        g = pf.gate_credentials({"AWIN_API_TOKEN": "SUPER_sekrit_value_123", "AWIN_PUBLISHER_ID": "5"})
        self.assertNotIn("SUPER_sekrit_value_123", str(g))   # value never surfaces


if __name__ == "__main__":
    unittest.main()
