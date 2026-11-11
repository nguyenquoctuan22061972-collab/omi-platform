"""QA — libs/video renderer (PRD-009 E). Phần nặng (PIL/numpy/ffmpeg) tự skip khi thiếu.

CI mặc định (python 3.11, không cài PIL/numpy/ffmpeg) sẽ chỉ chạy phần toán xfade; các
test dựng ảnh / nhạc / render sẽ SKIP (không FAIL) — vẫn xanh.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from libs.video.renderer import xfade_offsets  # noqa: E402 (thuần stdlib)

try:
    import numpy  # noqa: F401
    from PIL import Image  # noqa: F401
    from libs.video.renderer import Scene, VideoRenderer, ffmpeg_available
    HAS_DEPS = True
except Exception:
    HAS_DEPS = False

_SCRATCH = os.path.join(os.path.dirname(__file__), "_scratch")


class TestXfadeMath(unittest.TestCase):
    def test_offsets_single_gap(self):
        # hai clip 6s, crossfade 1s -> offset join đầu = 6 - 1 = 5
        self.assertEqual(xfade_offsets([6.0, 6.0], 1.0), [5.0])

    def test_offsets_chain(self):
        offs = xfade_offsets([7.0, 9.0, 8.0], 0.8)
        # join1 = 7-0.8=6.2 ; cum=7+9-0.8=15.2 ; join2=15.2-0.8=14.4
        self.assertAlmostEqual(offs[0], 6.2, places=3)
        self.assertAlmostEqual(offs[1], 14.4, places=3)
        self.assertEqual(len(offs), 2)

    def test_offsets_monotonic_increasing(self):
        offs = xfade_offsets([6, 6, 6, 6, 6], 0.8)
        self.assertEqual(offs, sorted(offs))


@unittest.skipUnless(HAS_DEPS, "cần Pillow + numpy")
class TestCompose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs(_SCRATCH, exist_ok=True)
        cls.r = VideoRenderer(width=640, height=360, workdir=_SCRATCH)

    def test_compose_scene_size_and_glyphs(self):
        png = os.path.join(_SCRATCH, "scene.png")
        sc = Scene(image_path="", duration=3, title="Ngày Con Tim Thức Dậy",
                   subtitle="Vết nứt — ánh sáng", kraft="Tập 01", kind="intro")
        out = self.r.compose_scene(sc, png)
        self.assertTrue(os.path.exists(out))
        with Image.open(out) as im:
            self.assertEqual(im.size, (640, 360))
            # ảnh không được toàn đen (có chữ + nền)
            self.assertGreater(len(im.convert("L").getcolors(maxcolors=100000) or []), 5)

    def test_music_bed_wav_duration(self):
        import wave
        wav = os.path.join(_SCRATCH, "m.wav")
        self.r.music_bed(2.0, wav)
        with wave.open(wav, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getframerate(), 44100)
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 2.0, delta=0.05)


@unittest.skipUnless(HAS_DEPS and (lambda: __import__("shutil").which("ffmpeg"))(),
                     "cần ffmpeg để render smoke")
class TestRenderSmoke(unittest.TestCase):
    def test_tiny_two_scene_render(self):
        os.makedirs(_SCRATCH, exist_ok=True)
        r = VideoRenderer(width=320, height=180, fps=12, crossfade=0.4,
                          workdir=os.path.join(_SCRATCH, "smoke"))
        scenes = [
            Scene(image_path="", duration=1.5, title="Một", kind="story"),
            Scene(image_path="", duration=1.5, title="Hai", kind="story", zoom="out"),
        ]
        out = os.path.join(_SCRATCH, "smoke.mp4")
        info = r.render(scenes, out, music=True)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 1000)
        self.assertEqual(info["scenes"], 2)
        self.assertIsNotNone(info["duration"])


if __name__ == "__main__":
    unittest.main()
