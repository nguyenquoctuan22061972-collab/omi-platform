"""Renderer MP4 thực tế: PIL dựng khung cảnh (chữ tiếng Việt) + ffmpeg chuyển động
Ken Burns & crossfade + numpy tổng hợp nhạc nền ambient.

Không gọi API ngoài khi render (asset đã tải về trước). Mỗi stage ffmpeg độc lập để dễ
kiểm thử và không fail toàn cục: nếu crossfade lỗi thì fallback sang nối cứng (concat).
"""
from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import wave
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

# Pillow/numpy được nạp LAZY bên trong method — nhờ vậy `sources`, `xfade_offsets` và
# phần định nghĩa class vẫn import được ở môi trường không cài PIL/numpy (vd CI 3.11),
# để test thuần-logic chạy và test render tự SKIP thay vì FAIL.

_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_FONT_CANDIDATES_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_FONT_CANDIDATES_SERIF = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _first_existing(paths: Sequence[str]) -> str:
    for p in paths:
        if os.path.exists(p):
            return p
    raise RuntimeError(f"Không tìm thấy font trong: {paths}")


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def xfade_offsets(durations: Sequence[float], crossfade: float) -> List[float]:
    """Offset cho từng mối nối xfade (clip 1..n-1).

    offset_k = (tổng d_0..d_k) - (k+1)*T. Trả list độ dài n-1.
    """
    offsets: List[float] = []
    cum = durations[0]
    for i in range(1, len(durations)):
        offsets.append(cum - crossfade)
        cum = cum + durations[i] - crossfade
    return offsets


@dataclass
class Scene:
    """Một cảnh = ảnh nền + chữ. duration tính bằng giây."""

    image_path: str
    duration: float = 6.0
    title: str = ""
    subtitle: str = ""
    kraft: str = ""            # dòng nhỏ phía trên (eyebrow), vd "TẬP 01"
    kind: str = "story"        # intro | story | quote | outro
    zoom: str = "in"           # in | out
    align: str = "center"      # center | bottom


@dataclass
class VideoRenderer:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    crossfade: float = 0.8     # giây
    brand: str = "HeartRise Stories"
    handle: str = "@HeartRiseStories"
    accent: Tuple[int, int, int] = (255, 173, 94)   # cam ấm – tông "HeartRise"
    workdir: str = "build"

    font_bold: str = field(default="", init=False)
    font_reg: str = field(default="", init=False)
    font_serif: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.font_bold = _first_existing(_FONT_CANDIDATES_BOLD)
        self.font_reg = _first_existing(_FONT_CANDIDATES_REG)
        self.font_serif = _first_existing(_FONT_CANDIDATES_SERIF)
        os.makedirs(self.workdir, exist_ok=True)

    # ---------- dựng khung cảnh (PIL) ----------
    def _fit_cover(self, img):
        """Scale + crop giữa để lấp đầy khung (giữ tỉ lệ)."""
        from PIL import Image
        tw, th = self.width, self.height
        iw, ih = img.size
        scale = max(tw / iw, th / ih)
        nw, nh = int(iw * scale + 0.5), int(ih * scale + 0.5)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw) // 2
        top = (nh - th) // 2
        return img.crop((left, top, left + tw, top + th))

    def _wrap(self, draw, text: str, font, max_w: int) -> List[str]:
        lines: List[str] = []
        for para in text.split("\n"):
            words = para.split(" ")
            cur = ""
            for w in words:
                trial = (cur + " " + w).strip()
                if draw.textlength(trial, font=font) <= max_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines

    def _vignette(self, size: Tuple[int, int], align: str):
        """Lớp tối để chữ nổi: gradient đậm đáy (bottom) hoặc tối đều + đáy (center)."""
        from PIL import Image
        w, h = size
        overlay = Image.new("L", (1, h), 0)
        px = overlay.load()
        for y in range(h):
            t = y / max(1, h - 1)
            if align == "bottom":
                a = int(235 * (t ** 2.4))           # tối mạnh về đáy
                base = 70
            else:
                a = int(170 * (t ** 1.8))
                base = 120
            px[0, y] = min(255, base + a)
        overlay = overlay.resize((w, h))
        black = Image.new("RGBA", (w, h), (8, 10, 16, 0))
        black.putalpha(overlay)
        return black

    def compose_scene(self, scene: Scene, out_png: str) -> str:
        from PIL import Image, ImageDraw, ImageFont
        W, H = self.width, self.height
        if scene.image_path and os.path.exists(scene.image_path):
            base = Image.open(scene.image_path).convert("RGB")
            base = self._fit_cover(base)
        else:
            base = Image.new("RGB", (W, H), (18, 20, 28))
        canvas = base.convert("RGBA")
        canvas.alpha_composite(self._vignette((W, H), scene.align))

        draw = ImageDraw.Draw(canvas)
        margin = int(W * 0.09)
        max_w = W - 2 * margin

        eyebrow_f = ImageFont.truetype(self.font_bold, 40)
        title_f = ImageFont.truetype(
            self.font_serif if scene.kind in ("quote", "intro", "outro") else self.font_bold,
            96 if scene.kind in ("intro", "outro") else 78,
        )
        sub_f = ImageFont.truetype(self.font_reg, 46)

        title_lines = self._wrap(draw, scene.title, title_f, max_w) if scene.title else []
        sub_lines = self._wrap(draw, scene.subtitle, sub_f, max_w) if scene.subtitle else []

        th = title_f.size + 18
        sh = sub_f.size + 12
        block_h = (len(title_lines) * th) + (len(sub_lines) * sh)
        if scene.kraft:
            block_h += eyebrow_f.size + 28
        if scene.align == "bottom":
            y = H - int(H * 0.14) - block_h
        else:
            y = (H - block_h) // 2

        def centered(text, font, fill, yy, shadow=True):
            tw = draw.textlength(text, font=font)
            x = (W - tw) / 2
            if shadow:
                draw.text((x + 3, yy + 3), text, font=font, fill=(0, 0, 0, 170))
            draw.text((x, yy), text, font=font, fill=fill)

        if scene.kraft:
            centered(scene.kraft.upper(), eyebrow_f, self.accent + (255,), y)
            # gạch nhỏ dưới eyebrow
            kw = draw.textlength(scene.kraft.upper(), font=eyebrow_f)
            lx = (W - kw) / 2
            draw.line([(lx, y + eyebrow_f.size + 12), (lx + kw, y + eyebrow_f.size + 12)],
                      fill=self.accent + (220,), width=3)
            y += eyebrow_f.size + 28
        for ln in title_lines:
            centered(ln, title_f, (255, 255, 255, 255), y)
            y += th
        for ln in sub_lines:
            centered(ln, sub_f, (226, 230, 238, 235), y)
            y += sh

        # branding góc + handle đáy
        brand_f = ImageFont.truetype(self.font_bold, 36)
        draw.text((margin, int(H * 0.055)), self.brand, font=brand_f,
                  fill=(255, 255, 255, 230))
        draw.rectangle([margin - 18, int(H * 0.055) - 6,
                        margin - 10, int(H * 0.055) + 40], fill=self.accent + (255,))
        handle_f = ImageFont.truetype(self.font_reg, 32)
        hw = draw.textlength(self.handle, font=handle_f)
        draw.text((W - margin - hw, H - int(H * 0.06)), self.handle, font=handle_f,
                  fill=(210, 214, 222, 210))

        canvas.convert("RGB").save(out_png, "PNG")
        return out_png

    # ---------- nhạc nền (numpy -> WAV stdlib) ----------
    def music_bed(self, duration: float, out_wav: str, seed: int = 7) -> str:
        import numpy as np

        sr = 44100
        n = int(duration * sr)
        t = np.linspace(0, duration, n, endpoint=False)

        # tiến trình hợp âm ấm, nâng (Am - F - C - G), vòng 8s
        chords = [
            [220.00, 261.63, 329.63],   # Am
            [174.61, 220.00, 261.63],   # F
            [261.63, 329.63, 392.00],   # C
            [196.00, 246.94, 293.66],   # G
        ]
        bar = duration / 4 if duration < 32 else 8.0
        out = np.zeros(n, dtype=np.float64)
        for i, freqs in enumerate([chords[k % 4] for k in range(max(4, int(math.ceil(duration / bar))))]):
            start = i * bar
            if start >= duration:
                break
            seg_n = int(min(bar, duration - start) * sr)
            lt = np.linspace(0, seg_n / sr, seg_n, endpoint=False)
            # attack/release mượt mỗi bar
            env = np.minimum(1.0, lt / 0.6) * np.minimum(1.0, (bar - lt) / 0.8 + 0.2)
            env = np.clip(env, 0, 1)
            seg = np.zeros(seg_n)
            for j, f in enumerate(freqs):
                amp = 0.5 / (j + 1.4)
                seg += amp * np.sin(2 * np.pi * f * lt)
                seg += 0.14 * amp * np.sin(2 * np.pi * f * 2 * lt)  # overtone
            s0 = i * int(bar * sr)
            out[s0:s0 + seg_n] += seg * env
        # LFO swell nhẹ + chuẩn hóa
        out *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * t)
        peak = np.max(np.abs(out)) or 1.0
        out = out / peak * 0.72
        # fade in/out toàn cục
        fi = int(min(2.0, duration * 0.15) * sr)
        fo = int(min(3.0, duration * 0.25) * sr)
        if fi > 0:
            out[:fi] *= np.linspace(0, 1, fi)
        if fo > 0:
            out[-fo:] *= np.linspace(1, 0, fo)
        # stereo widen nhẹ
        delay = int(0.012 * sr)
        right = np.concatenate([np.zeros(delay), out[:-delay]]) if delay < n else out
        stereo = np.stack([out, right], axis=1)
        pcm = np.int16(np.clip(stereo, -1, 1) * 32767)

        with wave.open(out_wav, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        return out_wav

    # ---------- ffmpeg ----------
    def _run(self, args: List[str]) -> None:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg lỗi:\n" + proc.stderr[-1500:])

    def _scene_clip(self, png: str, scene: Scene, out_mp4: str) -> None:
        frames = max(1, int(round(scene.duration * self.fps)))
        z_in = "min(zoom+0.0006,1.14)"
        z_out = "if(lte(zoom,1.0),1.14,max(zoom-0.0006,1.0))"
        z = z_in if scene.zoom == "in" else z_out
        # upscale x2 cho zoompan mượt, rồi zoompan về đúng khung
        vf = (
            f"scale={self.width*2}:{self.height*2},"
            f"zoompan=z='{z}':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={self.width}x{self.height}:fps={self.fps},"
            f"format=yuv420p"
        )
        self._run([
            "-loop", "1", "-i", png, "-t", f"{scene.duration}",
            "-vf", vf, "-r", str(self.fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", out_mp4,
        ])

    def _xfade_concat(self, clips: List[str], durations: List[float], out_mp4: str) -> None:
        T = self.crossfade
        inputs: List[str] = []
        for c in clips:
            inputs += ["-i", c]
        fc = []
        prev = "[0:v]"
        offsets = xfade_offsets(durations, T)
        for i in range(1, len(clips)):
            off = offsets[i - 1]
            label = f"[x{i}]" if i < len(clips) - 1 else "[vout]"
            fc.append(
                f"{prev}[{i}:v]xfade=transition=fade:duration={T}:offset={off:.3f}{label}"
            )
            prev = label
        filter_complex = ";".join(fc)
        self._run([
            *inputs, "-filter_complex", filter_complex,
            "-map", "[vout]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-pix_fmt", "yuv420p", out_mp4,
        ])

    def _hard_concat(self, clips: List[str], out_mp4: str) -> None:
        lst = os.path.join(self.workdir, "_concat.txt")
        with open(lst, "w") as f:
            for c in clips:
                f.write(f"file '{os.path.abspath(c)}'\n")
        self._run([
            "-f", "concat", "-safe", "0", "-i", lst,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", out_mp4,
        ])

    def _mux_audio(self, video: str, wav: str, out_mp4: str) -> None:
        self._run([
            "-i", video, "-i", wav,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", out_mp4,
        ])

    def probe(self, path: str) -> dict:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size:stream=codec_type,codec_name,width,height",
             "-of", "default=noprint_wrappers=1", path],
            capture_output=True, text=True,
        )
        info = {}
        for line in out.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info.setdefault(k, v)
        return info

    def render(self, scenes: Sequence[Scene], out_mp4: str,
               music: bool = True) -> dict:
        if not ffmpeg_available():
            raise RuntimeError("ffmpeg/ffprobe không có sẵn")
        if not scenes:
            raise ValueError("cần ít nhất 1 scene")
        os.makedirs(self.workdir, exist_ok=True)

        clips: List[str] = []
        durations: List[float] = []
        for i, sc in enumerate(scenes):
            png = os.path.join(self.workdir, f"scene_{i:02d}.png")
            self.compose_scene(sc, png)
            clip = os.path.join(self.workdir, f"clip_{i:02d}.mp4")
            self._scene_clip(png, sc, clip)
            clips.append(clip)
            durations.append(sc.duration)

        silent = os.path.join(self.workdir, "_video_silent.mp4")
        used_xfade = True
        if len(clips) == 1:
            shutil.copyfile(clips[0], silent)
        else:
            try:
                self._xfade_concat(clips, durations, silent)
            except Exception:
                used_xfade = False
                self._hard_concat(clips, silent)

        total = self.probe(silent).get("duration")
        total = float(total) if total else sum(durations)

        if music:
            wav = os.path.join(self.workdir, "_music.wav")
            self.music_bed(total, wav)
            self._mux_audio(silent, wav, out_mp4)
        else:
            shutil.copyfile(silent, out_mp4)

        info = self.probe(out_mp4)
        return {
            "path": out_mp4,
            "scenes": len(scenes),
            "crossfade": used_xfade,
            "music": music,
            "duration": info.get("duration"),
            "size": info.get("size"),
            "probe": info,
        }
