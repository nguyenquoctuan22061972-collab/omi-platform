"""QA — nối ContentPipeline với engine render (render=False, không cần ffmpeg)."""
import os
import sys
import unittest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, ".."))          # pipeline/
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", ".."))  # repo root
import video_runner as vr  # noqa: E402


class TestRunner(unittest.TestCase):
    def test_runner_stage_mapping_render_off(self):
        r = vr.EpisodeRunner("heartrise", 1, render=False)
        self.assertIn("script", r("script"))
        self.assertIn("planned", r("video"))
        self.assertIn("planned", r("publish"))
        self.assertIsNone(r.report)  # không render khi render=False

    def test_full_pipeline_completes(self):
        res = vr.run_episode_pipeline("wisdom", 1, render=False)
        self.assertTrue(res["done"])
        self.assertEqual(res["stages_completed"],
                         ["topic", "research", "script", "thumbnail", "video", "qa", "publish"])

    def test_channel_key_in_artifacts(self):
        res = vr.run_episode_pipeline("finance", 2, render=False)
        self.assertIn("finance", res["artifacts"]["video"])


if __name__ == "__main__":
    unittest.main()
