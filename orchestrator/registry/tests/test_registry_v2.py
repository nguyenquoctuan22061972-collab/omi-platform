"""QA — Capability Registry v2 (PRD-014 A)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.registry import CapabilityRegistryV2  # noqa: E402
from orchestrator.runtime.dispatcher import CapabilityDispatcher  # noqa: E402


class TestRegistryV2(unittest.TestCase):
    def setUp(self):
        self.r = CapabilityRegistryV2()
        self.r.register("pub", lambda c: 1, version="1.0", tags=["content"])
        self.r.register("pub", lambda c: 2, version="2.0", tags=["content"])
        self.r.register("old", lambda c: 0, version="1.0", deprecated=True)

    def test_resolve_latest_non_deprecated(self):
        self.assertEqual(self.r.resolve("pub"), "2.0")

    def test_resolve_constraint_gte(self):
        self.r.register("pub", lambda c: 3, version="3.0")
        self.assertEqual(self.r.resolve("pub", ">=2.0"), "3.0")

    def test_resolve_exact(self):
        self.assertEqual(self.r.resolve("pub", "1.0"), "1.0")

    def test_list_excludes_deprecated(self):
        names = [c["name"] for c in self.r.list()]
        self.assertNotIn("old", names)
        self.assertIn("pub", names)

    def test_bridge_to_dispatcher(self):
        d = CapabilityDispatcher()
        self.r.to_dispatcher(d)
        self.assertTrue(d.has("pub", "2.0"))
        self.assertFalse(d.has("old"))   # deprecated không bridge

    def test_stats(self):
        st = self.r.stats()
        self.assertEqual(st["capabilities"], 2)
        self.assertEqual(st["deprecated"], 1)


if __name__ == "__main__":
    unittest.main()
