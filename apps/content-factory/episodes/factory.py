"""Episode factory — Script → Voice → Video → QA cho BẤT KỲ kênh nào (1 engine, đổi preset).

Nối các mảnh: channels (preset) + script (kịch bản) + libs/video (render + narration + srt +
thumbnail) + libs/youtube (metadata DRY-RUN). Một hàm `make_episode` chạy trọn tập và trả
report + đường dẫn MP4/SRT/thumbnail/manifest. KHÔNG tự publish.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from libs.video import (  # noqa: E402
    get_channel, Scene, VideoRenderer, ffmpeg_available,
    download_first, probe_sources, SOURCES, write_srt, narration_from_env,
    NarrationSpec,
)
from libs.youtube import YouTubeRuntime, build_metadata  # noqa: E402

import script as _script  # noqa: E402  (cùng thư mục)

# Pool ảnh đã kiểm chứng tải được (200 + ảnh thật), đa nguồn fallback, map theo theme.
_U = "https://images.unsplash.com/photo-"
THEME_URLS: Dict[str, List[str]] = {
    "sunrise horizon calm": [f"{_U}1506744038136-46273834b3fb?w=1920&q=80",
                             "https://images.pexels.com/photos/355747/pexels-photo-355747.jpeg?auto=compress&cs=tinysrgb&w=1920"],
    "foggy sea boat": [f"{_U}1470071459604-3b5ec3a7fe05?w=1920&q=80",
                       "https://cdn.pixabay.com/photo/2016/11/29/05/45/astronomy-1867616_1280.jpg"],
    "long road dusk": [f"{_U}1476231682828-37e571bc172f?w=1920&q=80",
                       "https://images.pexels.com/photos/417074/pexels-photo-417074.jpeg?auto=compress&cs=tinysrgb&w=1920"],
    "sun rays mountain": [f"{_U}1469474968028-56623f02e42e?w=1920&q=80",
                          f"{_U}1506744038136-46273834b3fb?w=1920&q=80"],
    "forest light path": [f"{_U}1518495973542-4542c06a5843?w=1920&q=80",
                          f"{_U}1441974231531-c6227db76b6e?w=1920&q=80"],
    "walking trail green": [f"{_U}1441974231531-c6227db76b6e?w=1920&q=80",
                            f"{_U}1472214103451-9374bd1c798e?w=1920&q=80"],
    "peak summit sky": [f"{_U}1464822759023-fed622ff2c3b?w=1920&q=80",
                        f"{_U}1501785888041-af3ef285b470?w=1920&q=80"],
    "lake mountain calm": [f"{_U}1501785888041-af3ef285b470?w=1920&q=80",
                           f"{_U}1506744038136-46273834b3fb?w=1920&q=80"],
}
_FALLBACK_URLS = THEME_URLS["sunrise horizon calm"]


@dataclass
class EpisodeRequest:
    channel_key: str
    episode_no: int = 1
    title: str = ""
    music: bool = True
    want_voice: bool = True
    want_srt: bool = True
    want_thumb: bool = True
    limit_scenes: Optional[int] = None


def _rel(p: str) -> str:
    try:
        return os.path.relpath(p, _ROOT)
    except ValueError:
        return p


def _scene_plan(req: EpisodeRequest, channel) -> List[tuple]:
    """Trả list (urls, Scene-kwargs). HeartRise tập 01 dùng storyboard bespoke; còn lại
    sinh từ template script + pool ảnh theo theme."""
    if channel.key == "heartrise" and req.episode_no == 1:
        hp = os.path.join(_HERE, "heartrise_ep01")
        if hp not in sys.path:
            sys.path.insert(0, hp)
        import storyboard as sb  # bespoke trong heartrise_ep01/
        plan = []
        for s in sb.STORYBOARD:
            plan.append((s.urls, dict(duration=s.duration, title=s.title,
                         subtitle=s.subtitle, kraft=s.kraft, kind=s.kind,
                         zoom=s.zoom, align=s.align)))
        title = req.title or sb.TITLE
        return plan, title, sb.YT_TITLE, sb.YT_DESCRIPTION, sb.YT_TAGS

    beats = _script.generate(channel.brand, channel.niche, req.episode_no, req.title)
    # tiêu đề tập: ưu tiên req.title, else lấy từ cảnh intro (bỏ xuống dòng/trang trí)
    intro_title = beats[0].title.replace("\n", " ").strip().strip("“”\"").strip()
    title = req.title or intro_title or f"{channel.niche} — Khởi đầu"
    # thời lượng mỗi cảnh theo kind
    dur = {"intro": 7.0, "quote": 9.0, "outro": 8.0}
    plan = []
    for b in beats:
        urls = THEME_URLS.get(b.theme, _FALLBACK_URLS)
        plan.append((urls, dict(duration=dur.get(b.kind, 8.5), title=b.title,
                     subtitle=b.subtitle, kraft=b.kraft, kind=b.kind,
                     zoom=b.zoom, align=b.align)))
    yt_title = f"{title} | {channel.brand} — Tập {req.episode_no:02d}"
    yt_desc = (f"{channel.brand} — {channel.niche}. " +
               _script.script_text(beats)[:400] +
               "\n\n🖼️ Ảnh: tư liệu miễn phí (Pexels/Unsplash/Pixabay). "
               "🎧 Nhạc nền ambient gốc.")
    yt_tags = [channel.niche.lower(), channel.brand.lower(), "cảm hứng",
               "động lực", "câu chuyện"]
    return plan, title, yt_title, yt_desc, yt_tags


def check_resources() -> dict:
    results = [r.as_dict() for r in probe_sources(SOURCES)]
    return {"results": results,
            "accessible": [r["domain"] for r in results if r["ok"]],
            "blocked": [r["domain"] for r in results if not r["ok"]]}


def qa_check(mp4: str, renderer: VideoRenderer, srt: Optional[str],
             thumb: Optional[str]) -> dict:
    checks = []

    def add(name, ok, note=""):
        checks.append({"check": name, "ok": bool(ok), "note": note})

    info = renderer.probe(mp4) if os.path.exists(mp4) else {}
    add("mp4_exists", os.path.exists(mp4), _rel(mp4))
    add("has_video", info.get("codec_type") == "video" or "duration" in info,
        info.get("codec_name", ""))
    dur = float(info.get("duration", 0) or 0)
    add("duration_ok", 30 <= dur <= 240, f"{dur:.1f}s")
    add("size_ok", os.path.exists(mp4) and os.path.getsize(mp4) > 200_000,
        f"{os.path.getsize(mp4) if os.path.exists(mp4) else 0}B")
    if srt:
        add("srt_exists", os.path.exists(srt) and os.path.getsize(srt) > 10, _rel(srt))
    if thumb:
        add("thumb_exists", os.path.exists(thumb) and os.path.getsize(thumb) > 5000,
            _rel(thumb))
    passed = all(c["ok"] for c in checks)
    return {"passed": passed, "checks": checks}


def make_episode(req: EpisodeRequest, out_dir: Optional[str] = None) -> dict:
    channel = get_channel(req.channel_key)
    out_dir = out_dir or os.path.join(_HERE, "build", f"{channel.key}_ep{req.episode_no:02d}")
    assets = os.path.join(out_dir, "assets")
    os.makedirs(assets, exist_ok=True)

    report: dict = {
        "channel": channel.key, "brand": channel.brand, "handle": channel.handle,
        "episode_no": req.episode_no,
        "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }

    res = check_resources()
    report["resources"] = res
    if not res["accessible"]:
        raise RuntimeError("Không nguồn ảnh nào truy cập được. Bị chặn: "
                           + ", ".join(res["blocked"]))

    plan, title, yt_title, yt_desc, yt_tags = _scene_plan(req, channel)
    if req.limit_scenes:
        plan = plan[: req.limit_scenes]
    report["title"] = title

    scenes: List[Scene] = []
    for i, (urls, kw) in enumerate(plan):
        dest = os.path.join(assets, f"s{i:02d}.jpg")
        path = download_first(urls, dest)
        scenes.append(Scene(image_path=path, **kw))

    renderer = VideoRenderer(workdir=os.path.join(out_dir, "_work"),
                             brand=channel.brand, handle=channel.handle,
                             accent=channel.accent)

    # --- Voice (lồng tiếng) ---
    narration_wav = None
    if req.want_voice:
        provider = narration_from_env()
        if provider.name != "silent":
            os.makedirs(os.path.join(out_dir, "_work"), exist_ok=True)
            spec = NarrationSpec(text=_script_text_for(plan, scenes),
                                 lang=channel.lang, voice_hint=channel.voice_hint)
            wav = os.path.join(out_dir, "_work", "narration.wav")
            r = provider.synthesize(spec, wav)
            if r:
                narration_wav = r.path
                report["narration"] = {"provider": r.provider, "chars": r.chars,
                                       "duration": r.duration}
        if narration_wav is None:
            report["narration"] = {"provider": provider.name, "note": "no voice track"}

    # --- Render MP4 thật ---
    mp4 = os.path.join(out_dir, f"{channel.brand.replace(' ', '')}_EP{req.episode_no:02d}.mp4")
    render_info = renderer.render(scenes, mp4, music=req.music,
                                  narration_wav=narration_wav)
    render_info["path"] = _rel(mp4)
    report["render"] = render_info

    # --- Subtitle .srt ---
    srt = None
    if req.want_srt:
        srt = os.path.join(out_dir, f"{channel.brand.replace(' ', '')}_EP{req.episode_no:02d}.srt")
        write_srt(scenes, renderer.crossfade, srt)
        report["srt"] = _rel(srt)

    # --- Thumbnail riêng ---
    thumb = None
    if req.want_thumb:
        thumb = os.path.join(out_dir, "thumbnail.png")
        renderer.make_thumbnail(scenes[0], thumb)
        report["thumbnail"] = _rel(thumb)

    # --- YouTube metadata DRY-RUN (không publish) ---
    yt = YouTubeRuntime(os.environ)
    md = build_metadata(yt_title, yt_desc, tags=yt_tags, privacy="private")
    plan_yt = yt.upload(mp4, md, category=channel.yt_category,
                        thumbnail_ref=thumb or "")
    plan_yt["video"] = _rel(mp4)
    report["youtube_dry_run"] = plan_yt

    # --- QA ---
    report["qa"] = qa_check(mp4, renderer, srt, thumb)

    manifest = os.path.join(out_dir, "manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    report["manifest"] = _rel(manifest)
    return report


def _script_text_for(plan, scenes) -> str:
    """Lời đọc cho narration = ghép title+subtitle các cảnh (bỏ ký tự trang trí)."""
    parts = []
    for s in scenes:
        for seg in (s.title, s.subtitle):
            seg = (seg or "").replace("\n", " ").strip().strip("“”\"").strip()
            if seg:
                parts.append(seg)
    return " … ".join(parts)
