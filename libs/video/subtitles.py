"""Sinh phụ đề .srt khớp timeline các cảnh (tính cả crossfade). Thuần stdlib — testable."""
from __future__ import annotations

from typing import List, Sequence


def _ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _clean(text: str) -> str:
    # bỏ ngoặc kép trang trí ở đầu/cuối cho dễ đọc khi làm caption
    return (text or "").strip().strip("“”\"").strip()


def scene_windows(durations: Sequence[float], crossfade: float) -> List[tuple]:
    """(start, end) của từng cảnh trên timeline cuối, lát khít không chồng.

    Mỗi cảnh (trừ cảnh cuối) nhường `crossfade` giây cho mối nối kế tiếp, nên tổng
    = sum(d) - (n-1)*crossfade, đúng độ dài video thật.
    """
    out: List[tuple] = []
    cum = 0.0
    n = len(durations)
    for i, d in enumerate(durations):
        vis = d - (crossfade if i < n - 1 else 0.0)
        vis = max(0.1, vis)
        out.append((cum, cum + vis))
        cum += vis
    return out


def srt_from_scenes(scenes: Sequence, crossfade: float) -> str:
    """Dựng chuỗi .srt: mỗi cảnh 1 cue = title + subtitle (dòng riêng)."""
    durations = [getattr(s, "duration", 0.0) for s in scenes]
    windows = scene_windows(durations, crossfade)
    blocks: List[str] = []
    idx = 0
    for sc, (start, end) in zip(scenes, windows):
        lines = [_clean(getattr(sc, "title", "")), _clean(getattr(sc, "subtitle", ""))]
        text = "\n".join(l for l in lines if l)
        if not text:
            continue
        idx += 1
        blocks.append(f"{idx}\n{_ts(start)} --> {_ts(end)}\n{text}\n")
    return "\n".join(blocks) + ("\n" if blocks else "")


def write_srt(scenes: Sequence, crossfade: float, out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt_from_scenes(scenes, crossfade))
    return out_path
