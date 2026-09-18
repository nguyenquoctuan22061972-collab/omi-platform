"""QA — n8n Workflow Registry (PRD-009 D)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "runtime"))
import registry  # noqa: E402


class TestRegistry(unittest.TestCase):
    def test_has_core_workflows(self):
        ids = {r["id"] for r in registry.status()}
        for wf in ("WF001", "WF002", "WF003", "WF050"):
            self.assertIn(wf, ids)

    def test_existing_are_importable(self):
        st = {r["id"]: r for r in registry.status()}
        for wf in ("WF001", "WF002", "WF050"):
            self.assertEqual(st[wf]["activation"], "importable")
            self.assertTrue(st[wf]["has_file"])

    def test_future_is_planned(self):
        st = {r["id"]: r for r in registry.status()}
        self.assertEqual(st["WF003"]["activation"], "planned")
        self.assertTrue(st["WF003"]["planned"])

    def test_dependency_and_rollback(self):
        st = {r["id"]: r for r in registry.status()}
        self.assertIn("WF001", st["WF002"]["depends_on"])
        self.assertIn("WF002", registry.rollback_mapping())


if __name__ == "__main__":
    unittest.main()
