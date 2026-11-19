"""Lồng tiếng (voiceover) — lớp provider cắm được, để pipeline không phụ thuộc 1 nhà TTS.

Mặc định `SilentNarration` (không voice) để pipeline chạy offline/CI an toàn. Khi có file
narration sẵn → `FileNarration`. Khi có ELEVENLABS_API_KEY + voice → `ElevenLabsNarration`
gọi REST thật. Renderer nhận wav narration và trộn (có ducking) dưới nhạc nền.

Không nhà TTS nào được gọi khi chỉ import module; mọi call mạng là lazy và chỉ chạy khi
provider được chọn tường minh.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class NarrationSpec:
    text: str
    lang: str = "vi"
    voice_hint: str = "warm, calm"


@dataclass
class NarrationResult:
    path: str
    duration: float
    provider: str
    chars: int


def _ffmpeg(args) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg (narration) lỗi:\n" + proc.stderr[-1200:])


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def to_wav(src: str, dest_wav: str, sr: int = 44100) -> str:
    """Chuẩn hoá audio bất kỳ → wav stereo 44.1k để trộn ổn định."""
    _ffmpeg(["-i", src, "-ac", "2", "-ar", str(sr), dest_wav])
    return dest_wav


class NarrationProvider:
    name = "base"

    def synthesize(self, spec: NarrationSpec, out_wav: str) -> Optional[NarrationResult]:
        raise NotImplementedError


class SilentNarration(NarrationProvider):
    """Không lồng tiếng — trả None (pipeline dùng nhạc nền như cũ)."""

    name = "silent"

    def synthesize(self, spec, out_wav):
        return None


class FileNarration(NarrationProvider):
    """Dùng file narration có sẵn (wav/mp3/m4a...). Chuẩn hoá về wav."""

    name = "file"

    def __init__(self, src_path: str):
        self.src_path = src_path

    def synthesize(self, spec, out_wav):
        if not os.path.exists(self.src_path):
            raise FileNotFoundError(f"không thấy file narration: {self.src_path}")
        to_wav(self.src_path, out_wav)
        return NarrationResult(out_wav, probe_duration(out_wav), self.name,
                               len(spec.text or ""))


class ElevenLabsNarration(NarrationProvider):
    """Gọi ElevenLabs TTS REST thật. Chỉ dùng khi có api_key + voice_id.

    Tốn credit của người dùng → chỉ khởi tạo khi được chọn tường minh (vd from_env).
    """

    name = "elevenlabs"
    HOST = "api.elevenlabs.io"

    def __init__(self, api_key: str, voice_id: str,
                 model_id: str = "eleven_multilingual_v2"):
        if not api_key or not voice_id:
            raise ValueError("ElevenLabsNarration cần api_key và voice_id")
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id

    def synthesize(self, spec, out_wav):
        import json
        import ssl
        import urllib.request

        url = f"https://{self.HOST}/v1/text-to-speech/{self.voice_id}"
        payload = json.dumps({
            "text": spec.text,
            "model_id": self.model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("xi-api-key", self.api_key)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "audio/mpeg")

        ctx = ssl.create_default_context()
        ca = os.environ.get("CCR_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
        if os.path.exists(ca):
            try:
                ctx.load_verify_locations(ca)
            except Exception:
                pass
        mp3 = out_wav + ".mp3"
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            data = resp.read()
        if len(data) < 256:
            raise RuntimeError(f"ElevenLabs trả body quá nhỏ ({len(data)}B)")
        with open(mp3, "wb") as f:
            f.write(data)
        to_wav(mp3, out_wav)
        try:
            os.remove(mp3)
        except OSError:
            pass
        return NarrationResult(out_wav, probe_duration(out_wav), self.name,
                               len(spec.text or ""))


def from_env(env=None) -> NarrationProvider:
    """Chọn provider theo môi trường. Mặc định SilentNarration (an toàn, không tốn credit).

    - NARRATION_FILE=<path>            → FileNarration
    - ELEVENLABS_API_KEY + ELEVEN_VOICE_ID → ElevenLabsNarration
    """
    env = env if env is not None else os.environ
    f = env.get("NARRATION_FILE")
    if f:
        return FileNarration(f)
    key = env.get("ELEVENLABS_API_KEY")
    voice = env.get("ELEVEN_VOICE_ID")
    if key and voice:
        return ElevenLabsNarration(key, voice,
                                   env.get("ELEVEN_MODEL_ID", "eleven_multilingual_v2"))
    return SilentNarration()
