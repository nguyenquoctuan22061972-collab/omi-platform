"""QA — Agent Runtime (PRD-014 C)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.dispatcher import CapabilityDispatcher  # noqa: E402
from orchestrator.runtime.cost_guard import CostGuard  # noqa: E402
from orchestrator.agents import Agent, AgentPool, AgentState  # noqa: E402


class TestAgent(unittest.TestCase):
    def _agent(self, cost_guard=None):
        d = CapabilityDispatcher(); d.register("write", lambda c: "ok")
        return Agent("agent-1", ["write"], d, cost_guard=cost_guard)

    def test_run_success(self):
        a = self._agent()
        out = a.run("write", {"topic": "x"})
        self.assertTrue(out["ok"])
        self.assertEqual(a.state, AgentState.DONE)
        self.assertEqual(a.runs, 1)

    def test_capability_not_assigned(self):
        a = self._agent()
        out = a.run("delete")
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "capability_not_assigned")

    def test_budget_block(self):
        g = CostGuard(budget=0, default_cost=1)
        a = self._agent(cost_guard=g)
        out = a.run("write")
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "budget_exceeded")

    def test_charge_on_success(self):
        g = CostGuard(budget=10, cost_table={"write": 2})
        a = self._agent(cost_guard=g)
        a.run("write")
        self.assertEqual(g.spent, 2)

    def test_pool_capable(self):
        d = CapabilityDispatcher(); d.register("write", lambda c: 1)
        p = AgentPool()
        p.add(Agent("a1", ["write"], d)); p.add(Agent("a2", ["read"], d))
        self.assertEqual([a.id for a in p.capable("write")], ["a1"])


if __name__ == "__main__":
    unittest.main()
