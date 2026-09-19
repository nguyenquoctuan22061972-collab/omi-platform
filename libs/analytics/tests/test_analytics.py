"""QA — Analytics Layer (PRD-010 G)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.analytics import Analytics, MemoryProvider, new_session_id  # noqa: E402


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.a = Analytics(MemoryProvider())

    def test_session_id(self):
        self.assertTrue(new_session_id().startswith("ses_"))

    def test_track_event(self):
        s = new_session_id()
        ev = self.a.track("click", s, campaign="c1", url="/x")
        self.assertEqual(ev["type"], "click")
        self.assertTrue(ev["dry_run"])
        self.assertEqual(ev["props"]["url"], "/x")

    def test_invalid_event(self):
        with self.assertRaises(ValueError):
            self.a.track("hack", new_session_id())

    def test_revenue_and_conversion(self):
        s = new_session_id()
        self.a.track_revenue(s, 100.0, source="shopee", campaign="c1")
        self.a.track_conversion(s, kind="sale", campaign="c1")
        f = self.a.funnel()
        self.assertEqual(f["revenue"], 1)
        self.assertEqual(f["conversion"], 1)

    def test_attribution(self):
        s = new_session_id()
        self.a.track_conversion(s, campaign="c1")
        self.a.track_revenue(s, 50, campaign="c1")
        self.a.track_conversion(s, campaign="")  # direct
        attr = self.a.attribution()
        self.assertEqual(attr["c1"]["conversion"], 1)
        self.assertEqual(attr["c1"]["revenue"], 1)
        self.assertIn("(direct)", attr)


if __name__ == "__main__":
    unittest.main()
