"""QA — Worker Runtime (PRD-013 D)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.dispatcher import CapabilityDispatcher  # noqa: E402
from orchestrator.runtime.queue_orchestrator import QueueOrchestrator  # noqa: E402
from orchestrator.runtime.worker import Worker, WorkerState  # noqa: E402


class TestWorker(unittest.TestCase):
    def _setup(self, handler):
        q = QueueOrchestrator(base_backoff_s=0.0)
        d = CapabilityDispatcher(); d.register("job.do", handler)
        w = Worker("w1", q, d); w.start()
        return q, d, w

    def test_success(self):
        q, d, w = self._setup(lambda c: "done")
        q.enqueue("job.do", {"n": 1})
        out = w.run_once()
        self.assertEqual(out["result"], "succeeded")
        self.assertEqual(w.state, WorkerState.READY)
        self.assertEqual(w.processed, 1)

    def test_retry_state(self):
        def boom(c): raise RuntimeError("x")
        q, d, w = self._setup(boom)
        q.enqueue("job.do", max_retries=3)
        out = w.run_once()
        self.assertEqual(out["outcome"]["action"], "retry")
        self.assertEqual(w.state, WorkerState.RETRYING)

    def test_graceful_shutdown(self):
        q, d, w = self._setup(lambda c: "ok")
        w.stop()
        self.assertIsNone(w.run_once())
        self.assertEqual(w.state, WorkerState.STOPPED)

    def test_idle_when_empty(self):
        q, d, w = self._setup(lambda c: "ok")
        self.assertIsNone(w.run_once())
        self.assertEqual(w.state, WorkerState.READY)


if __name__ == "__main__":
    unittest.main()
