"""QA — Queue Orchestration (PRD-013 B). Reuse JobQueue + backoff + DLQ + metrics."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.queue_orchestrator import QueueOrchestrator  # noqa: E402


class TestQueueOrch(unittest.TestCase):
    def _clocked(self, base=1.0):
        t = {"v": 0.0}
        return QueueOrchestrator(base_backoff_s=base, clock=lambda: t["v"]), t

    def test_priority_order(self):
        q, _ = self._clocked()
        q.enqueue("low", priority=9); q.enqueue("high", priority=1)
        self.assertEqual(q.dequeue().kind, "high")

    def test_exponential_backoff(self):
        q, t = self._clocked(base=2.0)
        jid = q.enqueue("k", max_retries=3)
        job = q.dequeue()                      # attempts=1
        out = q.fail(job, "err")               # retry, delay=2*2^0=2
        self.assertEqual(out["action"], "retry")
        self.assertEqual(out["delay_s"], 2.0)
        self.assertIsNone(q.dequeue())         # chưa tới hạn → không lấy được
        t["v"] = 2.0
        self.assertIsNotNone(q.dequeue())      # đủ backoff → lấy được (attempts=2)
        self.assertEqual(q.retry_count, 1)

    def test_dead_letter(self):
        q, t = self._clocked(base=0.0)
        q.enqueue("k", max_retries=1)
        job = q.dequeue()                      # attempts=1 == max_retries
        out = q.fail(job, "boom")              # hết lượt → dead
        self.assertEqual(out["action"], "dead")
        self.assertEqual(q.stats()["dead_letter"], 1)

    def test_metrics_snapshot(self):
        q, _ = self._clocked()
        q.enqueue("a"); q.enqueue("b")
        snap = q.metrics_snapshot()
        self.assertEqual(snap["queue_size"], 2)
        self.assertIn("retry_count", snap)


if __name__ == "__main__":
    unittest.main()
