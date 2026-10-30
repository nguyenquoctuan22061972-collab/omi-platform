"""Video renderer (Content Factory): ảnh cảnh + giọng đọc + phụ đề → MP4 16:9 1080p.

Mỗi tập là một thư mục chứa `episode.json`, file giọng đọc, `words.json`
(mốc thời gian từng từ, lấy từ speech-to-text) và thư mục ảnh cảnh.
Ảnh được làm chuyển động kiểu Ken Burns bằng ffmpeg — không cần clip AI.

Usage:
    python3 render.py <episode_dir> [--preview SECONDS]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from typing import Dict, List, Tuple

FPS = 25
SUB_MAX_CHARS = 38
SENTENCE_END = re.compile(r'[.!?…]["\'”]?$')

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,120,120,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def load_episode(ep_dir: str) -> Dict:
    with open(os.path.join(ep_dir, "episode.json")) as f:
        ep = json.load(f)
    ep["dir"] = ep_dir
    return ep


def ass_time(t: float) -> str:
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def subtitle_chunks(words: List[Dict], max_chars: int = SUB_MAX_CHARS) -> List[Tuple[str, float, float]]:
    """Gom từ thành dòng phụ đề: ngắt ở cuối câu hoặc khi dài quá max_chars."""
    words = [w for w in words if w.get("type", "word") == "word"]
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        text = " ".join(x["text"] for x in cur)
        if len(text) > max_chars or SENTENCE_END.search(w["text"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [(" ".join(x["text"] for x in c), c[0]["start"], c[-1]["end"]) for c in chunks]


def ass_events(chunks: List[Tuple[str, float, float]], limit: float) -> List[str]:
    lines = []
    for k, (text, a, b) in enumerate(chunks):
        if a >= limit:
            break
        nxt = chunks[k + 1][1] if k + 1 < len(chunks) else b + 0.5
        end = min(max(b + 0.15, a + 0.8), nxt, limit)
        lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(end)},Sub,,0,0,0,,{text}")
    return lines


def scene_spans(scenes: List[Dict], total: float, limit: float) -> List[Tuple[str, float, float]]:
    """(ảnh, bắt đầu, kết thúc) cho từng cảnh, cắt ở limit."""
    spans = []
    for k, sc in enumerate(scenes):
        t0 = sc["start"]
        if t0 >= limit:
            break
        t1 = scenes[k + 1]["start"] if k + 1 < len(scenes) else total
        spans.append((sc["image"], t0, min(t1, limit)))
    return spans


def resolve_image(ep: Dict, name: str) -> str:
    img_dir = os.path.join(ep["dir"], ep.get("images_dir", "img"))
    seen = set()
    while name not in seen:
        path = os.path.join(img_dir, f"{name}.png")
        if os.path.exists(path):
            return path
        seen.add(name)
        name = ep.get("fallback", {}).get(name, name)
    raise FileNotFoundError(f"thiếu ảnh cảnh {name} (và không có fallback)")


def kenburns_filter(idx: int, dur: float) -> str:
    frames = max(int(dur * FPS), 1)
    style = idx % 4
    if style == 1:
        z = f"max(1.10-0.10*on/{frames},1.0)"
    else:
        z = f"min(1+0.10*on/{frames},1.10)"
    if style == 2:
        x, y = f"(iw-iw/zoom)*on/{frames}", "(ih-ih/zoom)/2"
    elif style == 3:
        x, y = f"(iw-iw/zoom)*(1-on/{frames})", "(ih-ih/zoom)/2"
    else:
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return (f"scale=3840:-2,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps={FPS},"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(dur - 0.4, 0):.2f}:d=0.4,format=yuv420p")


def duration(path: str) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                          "format=duration", "-of", "csv=p=0", path]))


def render(ep_dir: str, preview: float = 0.0) -> str:
    ep_dir = os.path.abspath(ep_dir)
    ep = load_episode(ep_dir)
    voice = os.path.join(ep_dir, ep["voice"])
    out_dir = os.path.join(ep_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    total = duration(voice)
    limit = min(preview, total) if preview else total

    with open(os.path.join(ep_dir, ep.get("words", "words.json"))) as f:
        words = json.load(f)["words"]
    subs = os.path.join(out_dir, "subs.ass")
    with open(subs, "w") as f:
        f.write(ASS_HEAD + "\n".join(ass_events(subtitle_chunks(words), limit)) + "\n")

    clips = []
    for k, (name, t0, t1) in enumerate(scene_spans(ep["scenes"], total, limit)):
        clip = os.path.join(out_dir, f"c{k:02d}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
                        "-i", resolve_image(ep, name), "-vf", kenburns_filter(k, t1 - t0),
                        "-t", f"{t1 - t0:.3f}", "-r", str(FPS), "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "20", clip], check=True)
        clips.append(clip)
    concat = os.path.join(out_dir, "list.txt")
    with open(concat, "w") as f:
        f.writelines(f"file '{c}'\n" for c in clips)

    final = os.path.join(out_dir, f"{ep['slug']}{'_preview' if limit < total else ''}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", concat, "-i", voice, "-t", f"{limit:.3f}", "-vf", f"ass={subs}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", final], check=True)
    return final


def main() -> None:
    ap = argparse.ArgumentParser(description="Dựng MP4 từ ảnh cảnh + giọng đọc + phụ đề")
    ap.add_argument("episode_dir")
    ap.add_argument("--preview", type=float, default=0.0, help="chỉ dựng N giây đầu")
    args = ap.parse_args()
    print(render(args.episode_dir, args.preview))


if __name__ == "__main__":
    main()
