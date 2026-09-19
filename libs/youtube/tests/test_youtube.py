"""QA — YouTube Runtime (PRD-010 D)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.youtube import YouTubeRuntime, build_metadata  # noqa: E402


class TestYouTube(unittest.TestCase):
    def test_metadata_builder_limits(self):
        md = build_metadata("t" * 200, "d" * 6000, tags=[str(i) for i in range(20)], privacy="public")
        self.assertEqual(len(md["title"]), 100)
        self.assertEqual(len(md["description"]), 5000)
        self.assertEqual(len(md["tags"]), 15)
        self.assertEqual(md["privacyStatus"], "public")

    def test_privacy_default_invalid(self):
        self.assertEqual(build_metadata("x", privacy="weird")["privacyStatus"], "private")

    def test_configured_from_env(self):
        yt = YouTubeRuntime(env={"YOUTUBE_CLIENT_ID": "a", "YOUTUBE_CLIENT_SECRET": "b",
                                 "YOUTUBE_REFRESH_TOKEN": "c"})
        self.assertTrue(yt.is_configured())
        self.assertFalse(YouTubeRuntime(env={}).is_configured())

    def test_upload_dry_run(self):
        yt = YouTubeRuntime(env={})
        res = yt.upload("vid.mp4", build_metadata("Hello"), category="tech",
                        thumbnail_ref="t.png", publish_at="2026-09-20T10:00:00Z")
        self.assertEqual(res["status"], "dry-run")
        self.assertEqual(res["playlist_env"], "YT_PLAYLIST_TECH")
        self.assertEqual(res["thumbnail"]["status"], "dry-run")
        self.assertEqual(res["schedule"]["status"], "scheduled-dry-run")

    def test_playlist_default(self):
        self.assertEqual(YouTubeRuntime(env={"YT_PLAYLIST_DEFAULT": "PLx"}).playlist_for("unknown"), "PLx")


if __name__ == "__main__":
    unittest.main()
