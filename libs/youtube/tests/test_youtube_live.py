"""QA — đường upload THẬT (guarded) + cổng an toàn privacy. Không gọi mạng."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.youtube import YouTubeRuntime, build_metadata  # noqa: E402
from libs.youtube.runtime import CATEGORY_ID  # noqa: E402


class TestLiveGate(unittest.TestCase):
    def test_live_without_credentials_stays_dry(self):
        yt = YouTubeRuntime(env={})
        res = yt.upload("v.mp4", build_metadata("Hi"), live=True)
        self.assertEqual(res["status"], "dry-run")
        self.assertIn("thiếu credential", res["note"])

    def test_default_still_dry_run(self):
        yt = YouTubeRuntime(env={"YOUTUBE_CLIENT_ID": "a", "YOUTUBE_CLIENT_SECRET": "b",
                                 "YOUTUBE_REFRESH_TOKEN": "c"})
        self.assertEqual(yt.upload("v.mp4", build_metadata("Hi"))["status"], "dry-run")

    def test_privacy_gate_downgrades_public(self):
        yt = YouTubeRuntime(env={})  # YT_ALLOW_PUBLIC chưa đặt
        md = yt._enforce_privacy(build_metadata("x", privacy="public"))
        self.assertEqual(md["privacyStatus"], "private")
        self.assertTrue(md["_privacy_downgraded"])

    def test_privacy_public_allowed_with_flag(self):
        yt = YouTubeRuntime(env={"YT_ALLOW_PUBLIC": "1"})
        md = yt._enforce_privacy(build_metadata("x", privacy="public"))
        self.assertEqual(md["privacyStatus"], "public")

    def test_category_map(self):
        self.assertEqual(CATEGORY_ID["finance"], "22")
        self.assertIn("default", CATEGORY_ID)


if __name__ == "__main__":
    unittest.main()
