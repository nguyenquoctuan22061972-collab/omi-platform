"""QA — Dispatch Engine (PRD-014 D)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import unittest  # noqa: E402
from orchestrator.runtime.dispatcher import CapabilityDispatcher  # noqa: E402
from orchestrator.runtime.dispatch_engine import DispatchEngine, NoCapableAgent  # noqa: E402
from orchestrator.runtime.queue_orchestrator import QueueOrchestrator  # noqa: E402
from orchestrator.agents import Agent, AgentPool  # noqa: E402


class TestDispatchEngine(unittest.TestCase):
    def _pool(self):
        d = CapabilityDispatcher(); d.register("write", lambda c: "ok")
        p = AgentPool()
        p.add(Agent("a1", ["write"], d)); p.add(Agent("a2", ["write"], d))
        return p

    def test_round_robin(self):
        de = DispatchEngine(self._pool(), strategy="round_robin")
        r1 = de.submit("write"); r2 = de.submit("write")
        self.assertEqual({r1["agent"], r2["agent"]}, {"a1", "a2"})

    def test_no_capable_agent(self):
        de = DispatchEngine(self._pool())
        with self.assertRaises(NoCapableAgent):
            de.route("delete")

    def test_least_busy(self):
        p = self._pool()
        de = DispatchEngine(p, strategy="least_busy")
        p.get("a1").runs = 5   # a1 bận hơn
        self.assertEqual(de.route("write").id, "a2")

    def test_submit_async_queue(self):
        de = DispatchEngine(self._pool(), queue=QueueOrchestrator())
        jid = de.submit_async("write", {"x": 1})
        self.assertTrue(jid.startswith("job_"))


if __name__ == "__main__":
    unittest.main()
