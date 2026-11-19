"""QA — nối ContentCalendar → JobQueue (lên lịch + đẩy job render)."""
import os
import sys
import unittest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, ".."))                       # calendar/
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", ".."))     # repo root
sys.path.insert(0, os.path.join(_HERE, "..", "..", "queue"))        # queue/
import scheduler  # noqa: E402
from calendar_engine import ContentCalendar  # noqa: E402
from jobqueue import JobQueue  # noqa: E402


class TestScheduler(unittest.TestCase):
    def test_seed_week_one_per_channel(self):
        cal = ContentCalendar()
        items = scheduler.seed_week(cal, "2026-11-20",
                                    channels=["heartrise", "finance", "aitech"])
        self.assertEqual(len(items), 3)
        self.assertEqual([i["channel"] for i in items],
                         ["heartrise", "finance", "aitech"])
        # ngày khác nhau
        days = {i["publish_at"][:10] for i in items}
        self.assertEqual(len(days), 3)

    def test_enqueue_due_creates_jobs(self):
        cal = ContentCalendar()
        q = JobQueue()
        scheduler.seed_week(cal, "2026-11-20", channels=["heartrise", "finance"])
        ids = scheduler.enqueue_due(cal, q, "2026-12-31T00:00:00Z")
        self.assertEqual(len(ids), 2)
        self.assertEqual(q.stats()["by_status"]["queued"], 2)
        job = q.dequeue()
        self.assertEqual(job.kind, scheduler.JOB_KIND)
        self.assertIn("channel", job.payload)

    def test_nothing_due_before_time(self):
        cal = ContentCalendar()
        q = JobQueue()
        scheduler.seed_week(cal, "2026-11-20", channels=["heartrise"])
        ids = scheduler.enqueue_due(cal, q, "2026-11-01T00:00:00Z")
        self.assertEqual(ids, [])


if __name__ == "__main__":
    unittest.main()
