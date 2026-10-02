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
