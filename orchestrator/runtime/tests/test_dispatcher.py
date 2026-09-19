"""QA — Capability Dispatcher (PRD-013 C)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.dispatcher import CapabilityDispatcher, CapabilityNotFound  # noqa: E402


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.d = CapabilityDispatcher()
        self.d.register("pub", lambda c: "v1", version="1.0")
        self.d.register("pub", lambda c: "v2", version="2.0")

    def test_resolve_latest(self):
        v, h = self.d.lookup("pub")
        self.assertEqual(v, "2.0")
        self.assertEqual(h(None), "v2")

    def test_resolve_explicit(self):
        v, h = self.d.lookup("pub", "1.0")
        self.assertEqual(v, "1.0")

    def test_not_found(self):
        with self.assertRaises(CapabilityNotFound):
            self.d.lookup("nope")

    def test_fallback_and_trace(self):
        self.d.register("backup", lambda c: "fb")
        name, v, h = self.d.dispatch("missing", fallback="backup")
        self.assertEqual(name, "backup")
        self.assertTrue(self.d.last_trace()["fallback_used"])

    def test_dispatch_trace_direct(self):
        name, v, h = self.d.dispatch("pub", "1.0")
        self.assertEqual((name, v), ("pub", "1.0"))
        self.assertFalse(self.d.last_trace()["fallback_used"])


if __name__ == "__main__":
    unittest.main()
