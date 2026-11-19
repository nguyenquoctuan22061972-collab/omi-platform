"""QA — libs/video asset sources (PRD-009 E, "video" stage real)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.video import sources as S  # noqa: E402
from libs.video import SOURCES, download_first, AssetUnavailable  # noqa: E402


class TestRegistry(unittest.TestCase):
    def test_three_known_sources(self):
        keys = {s.key for s in SOURCES}
        self.assertEqual(keys, {"pexels", "unsplash", "pixabay"})

    def test_each_source_has_probe_and_domain(self):
        for s in SOURCES:
            self.assertTrue(s.domain)
            self.assertTrue(s.probe_url.startswith("https://"))
            self.assertIn(s.domain, s.probe_url)
            self.assertTrue(s.license)

    def test_priority_order_is_stable(self):
        self.assertEqual([s.key for s in SOURCES], ["pexels", "unsplash", "pixabay"])


class TestImageMagic(unittest.TestCase):
    def test_detects_formats(self):
        pad = b"\x00" * 64
        self.assertTrue(S._looks_like_image(b"\xff\xd8\xff\xe0" + pad))        # JPEG
        self.assertTrue(S._looks_like_image(b"\x89PNG\r\n\x1a\n" + pad))       # PNG
        self.assertTrue(S._looks_like_image(b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + pad))
        self.assertTrue(S._looks_like_image(b"GIF89a" + pad))

    def test_rejects_html_and_short(self):
        self.assertFalse(S._looks_like_image(b"<!DOCTYPE html>" + b"\x00" * 64))
        self.assertFalse(S._looks_like_image(b"\xff\xd8"))  # quá ngắn


class TestDownloadFallback(unittest.TestCase):
    """download_first phải bỏ qua nguồn lỗi và lấy nguồn kế tiếp — không cần mạng."""

    def setUp(self):
        self._orig = S._http_fetch
        self.calls = []

    def tearDown(self):
        S._http_fetch = self._orig

    def test_first_fails_second_wins(self):
        good = b"\xff\xd8\xff\xe0" + b"\x00" * 1024

        def fake(url, timeout=25):
            self.calls.append(url)
            if "bad" in url:
                raise OSError("blocked domain")
            return good

        S._http_fetch = fake
        dest = os.path.join(os.path.dirname(__file__), "_tmp_asset.jpg")
        try:
            out = download_first(["https://bad/x.jpg", "https://ok/y.jpg"], dest)
            self.assertTrue(os.path.exists(out))
            # nguồn lỗi được thử (có retry) rồi chuyển sang nguồn tốt; cái cuối phải là "ok"
            self.assertIn("https://bad/x.jpg", self.calls)
            self.assertEqual(self.calls[-1], "https://ok/y.jpg")
        finally:
            if os.path.exists(dest):
                os.remove(dest)

    def test_all_fail_raises(self):
        def fake(url, timeout=25):
            raise OSError("blocked")

        S._http_fetch = fake
        dest = os.path.join(os.path.dirname(__file__), "_tmp_asset2.jpg")
        with self.assertRaises(AssetUnavailable):
            download_first(["https://a/1.jpg", "https://b/2.jpg"], dest)
        self.assertFalse(os.path.exists(dest))


@unittest.skipUnless(os.environ.get("VIDEO_NET_TESTS") == "1",
                     "network probe (đặt VIDEO_NET_TESTS=1 để chạy)")
class TestLiveProbe(unittest.TestCase):
    def test_at_least_one_source_up(self):
        results = S.probe_sources()
        self.assertTrue(any(r.ok for r in results),
                        msg=f"không nguồn nào tải được: {[r.as_dict() for r in results]}")


if __name__ == "__main__":
    unittest.main()
