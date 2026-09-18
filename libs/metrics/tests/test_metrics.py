"""QA — metrics export (PRD-008 D)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.metrics import MetricsRegistry, MockProvider, render_prometheus  # noqa: E402
from libs.metrics.registry import METRIC_NAMES  # noqa: E402


class TestMetrics(unittest.TestCase):
    def test_metric_names(self):
        for m in ("workflow_count", "queue_size", "adapter_status", "dashboard_latency_ms", "health_summary"):
            self.assertIn(m, METRIC_NAMES)

    def test_snapshot_defaults_zero(self):
        snap = MetricsRegistry().snapshot()
        self.assertEqual(set(snap), set(METRIC_NAMES))
        self.assertTrue(all(v == 0.0 for v in snap.values()))

    def test_provider_set(self):
        p = MockProvider()
        p.set("workflow_count", 3)
        self.assertEqual(MetricsRegistry(p).snapshot()["workflow_count"], 3.0)

    def test_invalid_metric(self):
        with self.assertRaises(KeyError):
            MockProvider().set("nope", 1)

    def test_render_prometheus(self):
        text = render_prometheus(MetricsRegistry(MockProvider({"queue_size": 5})).snapshot())
        self.assertIn("omi_queue_size 5", text)
        self.assertIn("# TYPE omi_workflow_count gauge", text)


if __name__ == "__main__":
    unittest.main()
