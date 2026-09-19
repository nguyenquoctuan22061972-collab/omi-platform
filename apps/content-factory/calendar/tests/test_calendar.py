"""QA — Content Calendar (PRD-010 E)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from calendar_engine import ContentCalendar, priority_of  # noqa: E402


class TestCalendar(unittest.TestCase):
    def test_priority_matrix(self):
        self.assertEqual(priority_of("youtube", "high"), 1)
        self.assertEqual(priority_of("unknown", "high"), 6)

    def test_schedule_and_due_order(self):
        c = ContentCalendar()
        c.schedule("A", "facebook", "2026-09-01T00:00:00Z", heat="normal")
        c.schedule("B", "youtube", "2026-09-01T00:00:00Z", heat="high")
        due = c.due("2026-09-02T00:00:00Z")
        self.assertEqual(due[0]["title"], "B")  # youtube high ưu tiên hơn

    def test_not_due_future(self):
        c = ContentCalendar()
        c.schedule("A", "tiktok", "2026-12-01T00:00:00Z")
        self.assertEqual(c.due("2026-09-02T00:00:00Z"), [])

    def test_publish(self):
        c = ContentCalendar()
        it = c.schedule("A", "youtube", "2026-09-01T00:00:00Z")
        c.mark_published(it)
        self.assertEqual(it["status"], "published")
        self.assertEqual(c.stats()["by_status"]["published"], 1)

    def test_retry_then_fail(self):
        c = ContentCalendar()
        it = c.schedule("A", "tiktok", "2026-09-01T00:00:00Z")
        self.assertEqual(c.mark_failed(it, "e1"), "retry")
        self.assertEqual(c.mark_failed(it, "e2"), "retry")
        self.assertEqual(c.mark_failed(it, "e3"), "failed")
        self.assertEqual(it["status"], "failed")


if __name__ == "__main__":
    unittest.main()
