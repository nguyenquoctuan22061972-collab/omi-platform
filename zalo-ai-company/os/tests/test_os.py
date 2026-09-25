"""QA — AI Company OS (PRD-016): registries, intent router, QA history, rollback log."""
import os
import sys
import tempfile
import unittest

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SRC)
from agent_registry import AgentRegistry      # noqa: E402
from skill_registry import SkillRegistry      # noqa: E402
from intent_router import IntentRouter        # noqa: E402
from qa_history import QAHistory              # noqa: E402
from rollback_log import RollbackLog          # noqa: E402

SEED_A = os.path.join(SRC, "agents.registry.json")
SEED_S = os.path.join(SRC, "skills.registry.json")


class TestOS(unittest.TestCase):
    def test_agent_registry_seed_and_lookup(self):
        r = AgentRegistry(); n = r.load_seed(SEED_A)
        self.assertEqual(n, 9)
        self.assertEqual(r.stats()["capacity"], 800)
        self.assertIn("ag-zalo-01", r.by_department("zalo"))
        self.assertIn("ag-eng-01", r.by_capability("deploy"))

    def test_agent_capacity_guard(self):
        r = AgentRegistry(capacity=1); r.register("a", [], "x")
        with self.assertRaises(OverflowError):
            r.register("b", [], "x")

    def test_skill_registry_seed(self):
        s = SkillRegistry(); n = s.load_seed(SEED_S)
        self.assertEqual(n, 6)
        self.assertEqual(s.stats()["capacity"], 400)
        self.assertIn("sk-zalo-send", s.by_category("messaging"))

    def test_intent_router_resolves_agent_skill(self):
        a = AgentRegistry(); a.load_seed(SEED_A)
        s = SkillRegistry(); s.load_seed(SEED_S)
        ir = IntentRouter(a, s)
        r = ir.route("Cho mình xin báo giá gói Premium")
        self.assertEqual(r["intent"], "sales_inquiry")
        self.assertEqual(r["department"], "sales")
        self.assertEqual(r["agent_id"], "ag-sales-01")
        self.assertEqual(r["skill_id"], "sk-sales-quote")

    def test_intent_fallback(self):
        r = IntentRouter().route("xin chào")
        self.assertEqual(r["intent"], "general")
        self.assertLess(r["confidence"], 0.5)

    def test_qa_history_redacts_and_summarizes(self):
        with tempfile.TemporaryDirectory() as d:
            h = QAHistory(os.path.join(d, "qa.json"))
            h.record("architecture", "arch check", "PASS")
            h.record("security", "secret scan", "PASS", meta={"access_token": "abc123secret"})
            self.assertEqual(h.summary()["pass"], 2)
            sec = h.query(gate="security")[0]
            self.assertEqual(sec["meta"]["access_token"], "***redacted***")
            # reload persists
            self.assertEqual(len(QAHistory(os.path.join(d, "qa.json")).records), 2)

    def test_qa_history_invalid_gate(self):
        with self.assertRaises(ValueError):
            QAHistory().record("nope", "x", "PASS")

    def test_rollback_log(self):
        with tempfile.TemporaryDirectory() as d:
            rl = RollbackLog(os.path.join(d, "rb.json"))
            rl.record("WF004", "post-deploy fail", "v2", "v1")
            self.assertEqual(rl.last()["target"], "WF004")
            self.assertEqual(len(RollbackLog(os.path.join(d, "rb.json")).list()), 1)


if __name__ == "__main__":
    unittest.main()
