"""QA — Cost Guard (PRD-014 E)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.cost_guard import CostGuard  # noqa: E402
from libs.metrics import MockProvider  # noqa: E402


class TestCostGuard(unittest.TestCase):
    def test_charge_and_remaining(self):
        g = CostGuard(budget=10, cost_table={"a": 3})
        self.assertTrue(g.charge("a")["ok"])
        self.assertAlmostEqual(g.remaining(), 7)

    def test_block_over_budget(self):
        g = CostGuard(budget=2, cost_table={"a": 3})
        out = g.charge("a")
        self.assertTrue(out["blocked"])
        self.assertEqual(g.spent, 0)
        self.assertEqual(g.blocked_count, 1)

    def test_default_cost_and_metrics(self):
        m = MockProvider()
        g = CostGuard(budget=5, default_cost=2, metrics=m)
        g.charge("unknown")
        self.assertEqual(m.collect()["cost_spent"], 2.0)

    def test_snapshot_and_reset(self):
        g = CostGuard(budget=10, cost_table={"a": 4})
        g.charge("a")
        self.assertEqual(g.snapshot()["spent"], 4)
        g.reset()
        self.assertEqual(g.spent, 0)


if __name__ == "__main__":
    unittest.main()
