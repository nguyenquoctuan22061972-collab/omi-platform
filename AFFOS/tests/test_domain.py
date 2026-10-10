"""QA — AFFOS domain (PRD-017): economics, events, agent/skill spec, Product Scout, builder report."""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core", "economics"))
sys.path.insert(0, os.path.join(ROOT, "core", "intelligence"))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "agents"))
sys.path.insert(0, os.path.join(ROOT, "skills"))
import economics, events, agent_spec, skill_spec, builder_report  # noqa: E402
from product_scout import ProductScout  # noqa: E402

CAND = [
    {"master_product_id": "MP-1", "demand": 100, "trend": 1.2, "conversion": 0.03, "epc": 0.5,
     "commission": 0.1, "content_fit": 0.8, "competition": 5, "production_cost": 2},
    {"master_product_id": "MP-2", "demand": 40, "trend": 1.0, "conversion": 0.02, "epc": 0.3,
     "commission": 0.08, "content_fit": 0.6, "competition": 8, "production_cost": 3},
]


class TestDomain(unittest.TestCase):
    def test_contribution_profit(self):
        r = economics.contribution_profit(31, ai_cost=5.2, content_cost=2, infrastructure_cost=1)
        self.assertEqual(r["contribution_profit"], 22.8)
        self.assertEqual(set(r["breakdown"]), set(economics.COST_KEYS))

    def test_opportunity_score_formula(self):
        s = economics.opportunity_score(100, 1.2, 0.03, 0.5, 0.1, 0.8, 5, 2)
        self.assertGreater(s, 0)
        with self.assertRaises(ValueError):
            economics.opportunity_score(1, 1, 1, 1, 1, 1, 0, 1)   # competition=0

    def test_ai_revenue_ratio(self):
        r = economics.ai_revenue_ratio(5.2, 31)
        self.assertEqual(r["ratio_pct"], 16.8)
        self.assertTrue(r["healthy"])

    def test_events_catalog(self):
        self.assertEqual(len(events.EVENTS), 11)
        e = events.make_event("opportunity.created", {"score": 1}, "MP-1")
        self.assertEqual(e["master_product_id"], "MP-1")
        with self.assertRaises(ValueError):
            events.make_event("nope")

    def test_agent_spec_and_permissions(self):
        with open(os.path.join(ROOT, "agents", "registry", "product_scout.json")) as f:
            spec = json.load(f)
        self.assertEqual(agent_spec.validate_agent(spec), [])
        self.assertTrue(agent_spec.can(spec, "create_opportunities"))
        self.assertFalse(agent_spec.can(spec, "spend_money"))

    def test_skill_spec(self):
        with open(os.path.join(ROOT, "skills", "definitions", "product_scout_skills.json")) as f:
            skills = json.load(f)["skills"]
        for s in skills:
            self.assertEqual(skill_spec.validate_skill(s), [])

    def test_product_scout_import_no_resourcewarning(self):
        # reloading the module re-runs its module-level SPEC load; must not leak a file handle
        import gc
        import importlib
        import warnings
        import product_scout
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            importlib.reload(product_scout)
            gc.collect()
        self.assertIsInstance(product_scout.SPEC, dict)        # SPEC structure intact
        self.assertIn("permissions", product_scout.SPEC)
        self.assertIn("cost_limit", product_scout.SPEC)

    def test_product_scout_scan_and_guardrail(self):
        ps = ProductScout()
        r = ps.scan(CAND, top_k=2)
        self.assertEqual(r["top"][0]["master_product_id"], "MP-1")  # điểm cao hơn
        self.assertTrue(all(ev["name"] == "opportunity.created" for ev in r["events"]))
        self.assertTrue(ps.try_spend()["blocked"])                  # CANNOT spend_money

    def test_cost_limit_enforced(self):
        ps = ProductScout(est_cost_per_scan=0.6)   # limit 1.0 -> chỉ ~1 scan
        r = ps.scan(CAND, top_k=5)
        self.assertLessEqual(r["scanned"], 2)
        self.assertLessEqual(r["spent"], 1.0)

    def test_builder_report_template(self):
        out = builder_report.render({"COMPLETED": ["schema", "economics"], "BLOCKED": ["OA token"]})
        self.assertIn("AFFOS BUILDER REPORT", out)
        for sec in builder_report.SECTIONS:
            self.assertIn(sec + ":", out)


if __name__ == "__main__":
    unittest.main()
