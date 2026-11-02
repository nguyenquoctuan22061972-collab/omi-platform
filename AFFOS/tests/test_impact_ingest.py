"""QA — AFFOS.1 Impact ingestion gate + Impact preflight. No credentials, no live call."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "impact"))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "ops"))

import impact_ingest                          # noqa: E402
import production_preflight as pf             # noqa: E402
import provenance                             # noqa: E402
from impact_live import ProductionTransport, Transport   # noqa: E402

CREDS_DB = {"IMPACT_ACCOUNT_SID": "SID", "IMPACT_AUTH_TOKEN": "tok", "DATABASE_URL": "postgresql://x"}


class TestImpactIngestGate(unittest.TestCase):
    def test_stops_without_approval(self):
        r = impact_ingest.run_ingestion(CREDS_DB, approved=False, transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")

    def test_stops_when_dry_run(self):
        r = impact_ingest.run_ingestion({"IMPACT_ACCOUNT_SID": "SID", "IMPACT_AUTH_TOKEN": "tok"},
                                        approved=True, transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertIn("DRY-RUN", r["reason"])

    def test_stops_without_production_transport(self):
        r = impact_ingest.run_ingestion(CREDS_DB, approved=True, transport=Transport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")


class TestImpactPreflight(unittest.TestCase):
    def test_credentials_missing_without_env(self):
        self.assertEqual(pf.gate_impact_credentials({})["status"], "MISSING")
        g = pf.gate_impact_credentials({"IMPACT_ACCOUNT_SID": "s", "IMPACT_AUTH_TOKEN": "t"})
        self.assertEqual(g["status"], "PRESENT")

    def test_adapter_gate_passes(self):
        self.assertEqual(pf.gate_impact_adapter({})["status"], "PASS")

    def test_whitelist_enabled(self):
        # CTO-approved: impact_production IS now whitelisted.
        self.assertIn("impact_production", provenance.PRODUCTION_SOURCES)
        self.assertEqual(pf.gate_impact_whitelist()["status"], "ENABLED")

    def test_run_impact_not_ready_without_external_deps(self):
        out = pf.run_impact({}, run_tests=False, probe_network=False)
        self.assertFalse(out["ready_for_impact_live_call"])    # creds/db/whitelist missing
        self.assertFalse(out["gates_ready_excluding_whitelist"])

    def test_credentials_never_leak(self):
        g = pf.gate_impact_credentials({"IMPACT_ACCOUNT_SID": "SECRETSID", "IMPACT_AUTH_TOKEN": "SECRETTOK"})
        self.assertNotIn("SECRETSID", str(g))
        self.assertNotIn("SECRETTOK", str(g))


if __name__ == "__main__":
    unittest.main()
