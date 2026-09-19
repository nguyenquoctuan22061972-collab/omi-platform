"""QA — Supervisor Runtime (PRD-013 E). Reuse libs.alerts for escalation."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from libs.alerts.engine import AlertEngine  # noqa: E402
from orchestrator.runtime.dispatcher import CapabilityDispatcher  # noqa: E402
from orchestrator.runtime.queue_orchestrator import QueueOrchestrator  # noqa: E402
from orchestrator.runtime.worker import Worker, WorkerState  # noqa: E402
from orchestrator.runtime.supervisor import Supervisor  # noqa: E402


class TestSupervisor(unittest.TestCase):
    def _make(self, n_jobs=5, clock=None):
        q = QueueOrchestrator(base_backoff_s=0.0, clock=clock)
        d = CapabilityDispatcher(); d.register("job.do", lambda c: "ok")
        w1 = Worker("w1", q, d); w2 = Worker("w2", q, d)
        for w in (w1, w2): w.start()
        sup = Supervisor(q, [w1, w2], clock=clock)
        for i in range(n_jobs):
            q.enqueue("job.do", {"i": i})
        return q, sup

    def test_drains_queue(self):
        q, sup = self._make(n_jobs=6)
        sup.run(max_ticks=50)
        self.assertEqual(q.depth(), 0)

    def test_health_healthy(self):
        q, sup = self._make(n_jobs=2)
        sup.run(max_ticks=20)
        h = sup.health()
        self.assertEqual(h["status"], "healthy")
        self.assertEqual(h["workers"], 2)

    def test_heartbeat_stale_escalation(self):
        t = {"v": 0.0}
        q, sup = self._make(n_jobs=1, clock=lambda: t["v"])
        sup.heartbeat_timeout_s = 10.0
        sup.tick()                    # ghi nhận heartbeat tại t=0
        t["v"] = 100.0                # thời gian trôi → quá hạn
        stale = sup.stale_workers()
        self.assertTrue(stale)
        alerts = AlertEngine(env={})  # không bật → dry-run, vẫn trả record
        sup.alerts = alerts
        esc = sup.escalate_failures()
        self.assertTrue(any(e["reason"] == "heartbeat_stale" for e in esc))

    def test_failed_worker_escalation(self):
        q, sup = self._make(n_jobs=0)
        sup.workers[0].state = WorkerState.FAILED
        esc = sup.escalate_failures()
        self.assertTrue(any(e["reason"] == "worker_failed" for e in esc))


if __name__ == "__main__":
    unittest.main()
