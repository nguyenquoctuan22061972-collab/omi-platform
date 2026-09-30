"""QA — AWIN GATE 1 preflight. Proves: no secret leak, redacted procedure, gated live call."""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "awin"))
import gate1_preflight as g1              # noqa: E402
from awin_live import ProductionTransport, Transport  # noqa: E402

# Placeholder fixture — NOT a credential. Used only to prove the value never leaks.
CANARY = "placeholder-fixture-value-000000"


class FakeProd(Transport):
    is_production = True
    def get(self, url, token):
        raise AssertionError("must never be called without approval+egress in this test")


class TestGate1Preflight(unittest.TestCase):
    def test_credential_status_never_prints_value(self):
        env = {"AWIN_API_TOKEN": CANARY, "AWIN_PUBLISHER_ID": "555"}
        st = g1.credential_status(env)
        blob = json.dumps(st)
        self.assertNotIn(CANARY, blob)            # value never surfaces
        self.assertTrue(st["AWIN_API_TOKEN"]["set"])
        self.assertEqual(st["AWIN_API_TOKEN"]["len"], len(CANARY))
        self.assertTrue(st["ready"])

    def test_missing_credentials_not_ready(self):
        st = g1.credential_status({})
        self.assertFalse(st["ready"])
        self.assertFalse(st["AWIN_API_TOKEN"]["set"])

    def test_procedure_is_redacted(self):
        env = {"AWIN_API_TOKEN": CANARY, "AWIN_PUBLISHER_ID": "555"}
        proc = json.dumps(g1.redacted_procedure(env))
        self.assertIn("***REDACTED***", proc)
        self.assertNotIn(CANARY, proc)            # token never rendered
        self.assertIn("Bearer", proc)

    def test_live_verify_stops_without_approval(self):
        env = {"AWIN_API_TOKEN": CANARY, "AWIN_PUBLISHER_ID": "555"}
        r = g1.live_verify(env, approved=False, transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")
        self.assertIn("approval", r["reason"].lower())

    def test_live_verify_stops_without_credentials(self):
        r = g1.live_verify({}, approved=True, transport=ProductionTransport())
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")

    def test_live_verify_refuses_non_production_transport(self):
        env = {"AWIN_API_TOKEN": CANARY, "AWIN_PUBLISHER_ID": "555"}
        r = g1.live_verify(env, approved=True, transport=Transport())  # is_production=False
        self.assertFalse(r["executed"])
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")

    def test_run_dry_is_not_verified_and_leak_free(self):
        env = {"AWIN_API_TOKEN": CANARY, "AWIN_PUBLISHER_ID": "555"}
        out = json.dumps(g1.run(env, approved=False))
        self.assertNotIn(CANARY, out)
        self.assertIn("NOT YET VERIFIED", out)


if __name__ == "__main__":
    unittest.main()
