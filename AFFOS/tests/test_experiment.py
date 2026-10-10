"""QA — Experiment lifecycle, policy/budget gate, kill switch, idempotency, result contract.
Offline; no credentials, no live call. Seed/mock data can never produce revenue proof."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "core", "attribution"))
sys.path.insert(0, os.path.join(ROOT, "core", "economics"))

import experiment as X        # noqa: E402
import provenance            # noqa: E402
from data_access import Repo  # noqa: E402


def _full_policy(**over):
    p = {"max_budget": 100, "max_loss": 50, "currency": "USD", "traffic_source": "organic",
         "measurement_window": "14d", "attribution_method": "last_click",
         "success_criteria": "net_profit>0", "stop_criteria": "loss>=max_loss",
         "paid_spend": 0, "ceo_approved": True}
    p.update(over)
    return p


class TestLifecycle(unittest.TestCase):
    def test_happy_path(self):
        e = X.Experiment("E1", "h", "C1", policy=_full_policy())
        self.assertEqual(e.status, "DRAFT")
        e.submit("ceo"); self.assertEqual(e.status, "NEEDS_APPROVAL")
        e.approve("ceo"); self.assertEqual(e.status, "APPROVED")
        e.start("ceo"); self.assertEqual(e.status, "RUNNING")
        e.measure("system"); self.assertEqual(e.status, "MEASURED")
        e.decide("WIN", "ceo"); self.assertEqual(e.status, "WIN")
        self.assertEqual(len(e.audit), 5)   # every transition logged
        self.assertEqual(e.audit[0]["from"], "DRAFT")

    def test_invalid_transition_blocked(self):
        e = X.Experiment("E2", policy=_full_policy())
        with self.assertRaises(X.InvalidTransition):
            e.start("ceo")                 # DRAFT → RUNNING not allowed
        with self.assertRaises(X.InvalidTransition):
            e.decide("WIN", "ceo")         # DRAFT → WIN not allowed

    def test_terminal_is_final(self):
        e = X.Experiment("E3", policy=_full_policy())
        e.submit("a"); e.kill("a", "stop")
        self.assertEqual(e.status, "KILL")
        with self.assertRaises(X.InvalidTransition):
            e.transition("RUNNING", "a")   # cannot leave terminal

    def test_audit_records_actor_reason(self):
        e = X.Experiment("E4", policy=_full_policy())
        e.submit("quoctuan", "ready for review")
        a = e.audit[-1]
        self.assertEqual(a["actor"], "quoctuan")
        self.assertEqual(a["reason"], "ready for review")
        self.assertIn("ts", a)


class TestPolicyBudgetGate(unittest.TestCase):
    def test_approval_requires_ceo(self):
        e = X.Experiment("E5", policy=_full_policy(ceo_approved=False))
        e.submit("a")
        with self.assertRaises(X.PolicyViolation):
            e.approve("a")

    def test_running_requires_complete_policy(self):
        e = X.Experiment("E6", policy=_full_policy(max_budget=None))
        e.submit("a"); e.approve("a")
        with self.assertRaises(X.PolicyViolation):
            e.start("a")                   # missing max_budget → blocked

    def test_paid_spend_requires_ceo_approval(self):
        g = X.policy_gate(_full_policy(paid_spend=20, ceo_approved=False))
        self.assertFalse(g["ok"])
        self.assertIn("paid_spend_requires_ceo_approval", g["blocked"])

    def test_default_paid_spend_zero_ok(self):
        self.assertTrue(X.policy_gate(_full_policy())["ok"])

    def test_kill_switch_from_running(self):
        e = X.Experiment("E7", policy=_full_policy())
        e.submit("a"); e.approve("a"); e.start("a")
        e.kill("a", "loss cap hit")
        self.assertEqual(e.status, "KILL")


class TestIdempotency(unittest.TestCase):
    def test_duplicate_event_is_noop(self):
        e = X.Experiment("E8", policy=_full_policy())
        r1 = e.submit("a", event_id="evt-1")
        r2 = e.submit("a", event_id="evt-1")   # replay
        self.assertFalse(r1["idempotent"])
        self.assertTrue(r2["idempotent"])
        self.assertEqual(e.status, "NEEDS_APPROVAL")
        self.assertEqual(len(e.audit), 1)       # logged once only


class TestResultContract(unittest.TestCase):
    def _seed(self, repo, amount, status, currency="USD", ds="SEEDED", source="seed", verified=False, linked=False):
        tl = ce = ""
        if linked:
            repo.insert("campaigns", {"id": "C1", "offer_id": "OF-1", "name": "exp", "status": "active"})
            repo.insert("tracking_links", {"id": "L1", "campaign_id": "C1", "offer_id": "OF-1",
                                           "slug": "s", "target_url": "https://x"})
            tl = "L1"; ce = "CE1"
            repo.insert("click_events", {"id": ce, "tracking_link_id": tl, "ts": "t", "event_subtype": "SEEDED_CLICK",
                        **provenance.provenance(source, ce, ds, currency=currency, is_verified=verified)})
        cv = "CV1"
        repo.insert("conversion_events", {"id": cv, "click_event_id": ce, "offer_id": "OF-1",
                    "order_value": amount, "status": status, "ts": "t", "event_subtype": "SEEDED_CONVERSION",
                    **provenance.provenance(source, cv, ds, currency=currency, is_verified=verified)})
        repo.insert("commissions", {"id": "CO1", "conversion_event_id": cv, "amount": amount, "status": status,
                    **provenance.provenance(source, "CO1", ds, currency=currency, is_verified=verified)})

    def test_seed_data_never_revenue_proven(self):
        repo = Repo(data_state="SEEDED")
        e = X.Experiment("E9", campaign_id="C1", policy=_full_policy())
        self._seed(repo, 100, "APPROVED", linked=True)   # seeded + linked, still not production
        r = X.experiment_result(repo, e)
        self.assertFalse(r["revenue_proven"])
        self.assertEqual(r["evidence_class"], "FORECAST_OR_SEED")
        self.assertEqual(r["currency"], "USD")
        self.assertEqual(r["net_revenue"], 100.0)        # confirmed counts, but unproven

    def test_missing_attribution_blocks_proof(self):
        repo = Repo(data_state="SEEDED")
        e = X.Experiment("E10", campaign_id="C1", policy=_full_policy())
        self._seed(repo, 100, "APPROVED", linked=False)  # no tracking_link_id
        r = X.experiment_result(repo, e)
        self.assertFalse(r["attribution_linked"])
        self.assertFalse(r["revenue_proven"])


if __name__ == "__main__":
    unittest.main()
