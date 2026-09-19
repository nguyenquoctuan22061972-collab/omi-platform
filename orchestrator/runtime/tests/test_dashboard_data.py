"""QA — Runtime Dashboard Data (PRD-014 F)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import json  # noqa: E402
import unittest  # noqa: E402
from orchestrator.runtime.queue_orchestrator import QueueOrchestrator  # noqa: E402
from orchestrator.runtime.cost_guard import CostGuard  # noqa: E402
from orchestrator.registry import CapabilityRegistryV2  # noqa: E402
from orchestrator.runtime.dashboard_data import build_dashboard  # noqa: E402


class TestDashboard(unittest.TestCase):
    def test_aggregate_and_json(self):
        q = QueueOrchestrator(); q.enqueue("a"); q.enqueue("b")
        g = CostGuard(budget=10, cost_table={"a": 3}); g.charge("a")
        r = CapabilityRegistryV2(); r.register("a", lambda c: 1)
        data = build_dashboard(queue=q, cost_guard=g, registry=r)
        self.assertIn("queue", data["sections"])
        self.assertIn("cost", data["sections"])
        self.assertIn("capabilities", data["sections"])
        self.assertEqual(data["sections"]["metrics"]["queue_size"], 2)
        self.assertEqual(data["sections"]["metrics"]["cost_spent"], 3)
        json.dumps(data)   # phải JSON-serializable

    def test_empty(self):
        data = build_dashboard()
        self.assertIn("metrics", data["sections"])
        json.dumps(data)


if __name__ == "__main__":
    unittest.main()
