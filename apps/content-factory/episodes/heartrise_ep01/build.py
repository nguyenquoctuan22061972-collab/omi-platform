"""Build HeartRise EP01 — MP4 THỰC TẾ.

Luồng: probe nguồn ảnh → tải asset (fallback khi domain bị chặn) → render MP4
(Ken Burns + crossfade + nhạc nền) → dựng metadata YouTube DRY-RUN (không tự publish)
→ ghi manifest.json.

Chạy:
    python apps/content-factory/episodes/heartrise_ep01/build.py [--out DIR] [--no-music]

KHÔNG tự động upload/publish YouTube: chỉ sinh kế hoạch qua libs.youtube (dry-run).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

# repo root để import libs.* (giống quy ước libs/youtube/tests). Thư mục `content-factory`
# có dấu gạch ngang nên không phải package Python — ta nạp storyboard theo đường dẫn.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from libs.video import (  # noqa: E402
    SOURCES, probe_sources, download_first, Scene, VideoRenderer, ffmpeg_available,
)
from libs.youtube import YouTubeRuntime, build_metadata  # noqa: E402

import storyboard as sb  # type: ignore  # noqa: E402


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path, _ROOT)
    except ValueError:
        return path


def check_resources() -> dict:
    """Bước 1: kiểm tra khả năng tải từ Pexels/Pixabay/Unsplash."""
    results = [r.as_dict() for r in probe_sources(SOURCES)]
    accessible = [r["domain"] for r in results if r["ok"]]
    blocked = [r["domain"] for r in results if not r["ok"]]
    return {"results": results, "accessible": accessible, "blocked": blocked}


def build(out_dir: str | None = None, music: bool = True,
          limit_scenes: int | None = None) -> dict:
    out_dir = out_dir or os.path.join(_HERE, "build")
    assets_dir = os.path.join(out_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    report: dict = {
        "episode": sb.EPISODE_ID,
        "channel": sb.CHANNEL,
        "title": sb.TITLE,
        "built_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }

    # --- Bước 1: probe nguồn ---
    res = check_resources()
    report["resources"] = res
    if not res["accessible"]:
        raise RuntimeError(
            "Không nguồn ảnh nào truy cập được. Bị chặn: " + ", ".join(res["blocked"])
        )

    # --- Bước 2: tải asset theo cảnh (fallback đa nguồn) ---
    specs = sb.STORYBOARD[: limit_scenes] if limit_scenes else sb.STORYBOARD
    scenes: list[Scene] = []
    asset_log: list[dict] = []
    for spec in specs:
        dest = os.path.join(assets_dir, f"{spec.key}.jpg")
        path = download_first(spec.urls, dest)
        asset_log.append({"scene": spec.key, "file": _rel(path),
                          "candidates": len(spec.urls)})
        scenes.append(Scene(
            image_path=path, duration=spec.duration, title=spec.title,
            subtitle=spec.subtitle, kraft=spec.kraft, kind=spec.kind,
            zoom=spec.zoom, align=spec.align,
        ))
    report["assets"] = asset_log

    # --- Bước 3: render MP4 thực tế ---
    out_mp4 = os.path.join(out_dir, "HeartRise_EP01.mp4")
    renderer = VideoRenderer(workdir=os.path.join(out_dir, "_work"),
                             brand=sb.CHANNEL, handle=sb.HANDLE)
    render_info = renderer.render(scenes, out_mp4, music=music)
    render_info["path"] = _rel(render_info["path"])
    report["render"] = render_info

    # --- Bước 4: metadata YouTube DRY-RUN (KHÔNG publish) ---
    yt = YouTubeRuntime(os.environ)
    md = build_metadata(sb.YT_TITLE, sb.YT_DESCRIPTION, tags=sb.YT_TAGS,
                        privacy="private")
    plan = yt.upload(out_mp4, md, category="inspire")
    plan["video"] = _rel(out_mp4)
    report["youtube_dry_run"] = plan

    # --- manifest ---
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    report["manifest"] = _rel(manifest_path)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build HeartRise EP01 MP4")
    ap.add_argument("--out", default=None, help="thư mục output")
    ap.add_argument("--no-music", action="store_true", help="không chèn nhạc nền")
    ap.add_argument("--probe-only", action="store_true",
                    help="chỉ kiểm tra nguồn rồi thoát")
    args = ap.parse_args(argv)

    if args.probe_only:
        print(json.dumps(check_resources(), ensure_ascii=False, indent=2))
        return 0

    if not ffmpeg_available():
        print("ffmpeg/ffprobe không có — không thể render.", file=sys.stderr)
        return 2

    rep = build(out_dir=args.out, music=not args.no_music)
    r = rep["render"]
    print(f"✅ MP4: {r['path']}  ({r.get('duration')}s, {r.get('size')}B, "
          f"{r['scenes']} cảnh, crossfade={r['crossfade']}, music={r['music']})")
    print(f"📄 manifest: {rep['manifest']}")
    print(f"🔒 YouTube: {rep['youtube_dry_run']['status']} "
          f"(configured={rep['youtube_dry_run']['configured']}) — KHÔNG tự publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
