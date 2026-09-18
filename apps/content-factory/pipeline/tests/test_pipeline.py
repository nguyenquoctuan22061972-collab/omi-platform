"""QA — Content Pipeline state machine (PRD-009 E)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pipeline import ContentPipeline, STAGES  # noqa: E402


class TestPipeline(unittest.TestCase):
    def test_stage_order(self):
        self.assertEqual(STAGES, ["topic", "research", "script", "thumbnail", "video", "qa", "publish"])

    def test_starts_at_topic(self):
        p = ContentPipeline("OMI")
        self.assertEqual(p.current(), "topic")
        self.assertFalse(p.is_done())

    def test_advance_transitions(self):
        p = ContentPipeline("OMI")
        r = p.advance()
        self.assertEqual(r["stage"], "topic")
        self.assertEqual(r["next"], "research")

    def test_run_all_completes(self):
        p = ContentPipeline("OMI")
        res = p.run_all()
        self.assertTrue(res["done"])
        self.assertEqual(res["stages_completed"], STAGES)
        self.assertEqual(len(res["artifacts"]), len(STAGES))

    def test_custom_runner_mock(self):
        p = ContentPipeline("OMI")
        res = p.run_all(runner=lambda s: f"X-{s}")
        self.assertEqual(res["artifacts"]["publish"], "X-publish")


if __name__ == "__main__":
    unittest.main()
