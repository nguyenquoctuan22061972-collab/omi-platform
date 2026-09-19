"""QA — Metrics collectors (PRD-012 A)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.metrics.collectors import build_snapshot, metrics_text  # noqa: E402
from libs.metrics.registry import METRIC_NAMES  # noqa: E402


class TestCollectors(unittest.TestCase):
    def test_snapshot_keys(self):
        snap = build_snapshot(health_ready=True, queue_pending=3, adapters_enabled=2, workflow_count=4)
        self.assertEqual(set(snap), set(METRIC_NAMES))
        self.assertEqual(snap["health_summary"], 1.0)
        self.assertEqual(snap["queue_size"], 3)
        self.assertEqual(snap["adapter_status"], 2)
        self.assertEqual(snap["workflow_count"], 4)

    def test_health_degraded(self):
        self.assertEqual(build_snapshot(health_ready=False)["health_summary"], 0.0)

    def test_metrics_text(self):
        txt = metrics_text(queue_pending=5)
        self.assertIn("omi_queue_size 5", txt)
        self.assertIn("# TYPE omi_health_summary gauge", txt)


if __name__ == "__main__":
    unittest.main()
