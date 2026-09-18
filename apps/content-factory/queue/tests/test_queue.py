"""QA — AI Job Queue (PRD-009 A). Import module trực tiếp (tránh trùng tên 'queue' stdlib)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from jobqueue import Job, JobQueue  # noqa: E402


class TestJobQueue(unittest.TestCase):
    def setUp(self):
        self.q = JobQueue()

    def test_priority_order(self):
        self.q.enqueue(Job("low", {}, priority=9))
        self.q.enqueue(Job("high", {}, priority=1))
        self.assertEqual(self.q.dequeue().kind, "high")

    def test_complete(self):
        self.q.enqueue(Job("t", {}))
        job = self.q.dequeue()
        self.q.complete(job)
        self.assertEqual(job.status, "succeeded")
        self.assertEqual(self.q.stats()["by_status"]["succeeded"], 1)

    def test_retry_then_dead_letter(self):
        self.q.enqueue(Job("t", {}, max_retries=2))
        # attempt 1
        job = self.q.dequeue(); self.assertEqual(self.q.fail(job, "e1"), "requeued")
        # attempt 2 (== max_retries) → dead
        job = self.q.dequeue(); self.assertEqual(self.q.fail(job, "e2"), "dead")
        self.assertEqual(job.status, "dead")
        self.assertEqual(len(self.q.dead_letter), 1)

    def test_timeline_records_transitions(self):
        self.q.enqueue(Job("t", {}))
        job = self.q.dequeue()
        self.q.complete(job)
        statuses = [e["status"] for e in job.timeline]
        self.assertEqual(statuses, ["queued", "running", "succeeded"])

    def test_stats_and_history(self):
        for i in range(3):
            self.q.enqueue(Job("t", {"i": i}))
        while True:
            j = self.q.dequeue()
            if not j:
                break
            self.q.complete(j)
        self.assertEqual(len(self.q.history), 3)
        self.assertEqual(self.q.stats()["total"], 3)


if __name__ == "__main__":
    unittest.main()
