"""QA — lớp narration (không gọi mạng/ffmpeg; chỉ chọn provider + guard)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.video import narration as N  # noqa: E402
from libs.video import (narration_from_env, SilentNarration, FileNarration,  # noqa: E402
                        ElevenLabsNarration, NarrationSpec)


class TestProviderSelection(unittest.TestCase):
    def test_default_is_silent(self):
        p = narration_from_env({})
        self.assertIsInstance(p, SilentNarration)
        self.assertIsNone(p.synthesize(NarrationSpec("x"), "/tmp/none.wav"))

    def test_file_provider_chosen(self):
        p = narration_from_env({"NARRATION_FILE": "/tmp/a.wav"})
        self.assertIsInstance(p, FileNarration)

    def test_elevenlabs_chosen_when_keys_present(self):
        p = narration_from_env({"ELEVENLABS_API_KEY": "k", "ELEVEN_VOICE_ID": "v"})
        self.assertIsInstance(p, ElevenLabsNarration)

    def test_elevenlabs_requires_both(self):
        # chỉ có key, thiếu voice → về silent
        self.assertIsInstance(narration_from_env({"ELEVENLABS_API_KEY": "k"}),
                              SilentNarration)
        with self.assertRaises(ValueError):
            ElevenLabsNarration("", "")

    def test_file_missing_raises(self):
        p = FileNarration("/no/such/file.wav")
        with self.assertRaises(FileNotFoundError):
            p.synthesize(NarrationSpec("hi"), "/tmp/out.wav")

    def test_names(self):
        self.assertEqual(SilentNarration().name, "silent")
        self.assertEqual(FileNarration("x").name, "file")
        self.assertEqual(ElevenLabsNarration("k", "v").name, "elevenlabs")


if __name__ == "__main__":
    unittest.main()
