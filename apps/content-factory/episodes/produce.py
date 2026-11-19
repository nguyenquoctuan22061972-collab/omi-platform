"""CLI sản xuất 1 tập cho BẤT KỲ kênh nào — dùng chung 1 engine.

Ví dụ:
    python apps/content-factory/episodes/produce.py --list
    python apps/content-factory/episodes/produce.py --channel heartrise
    python apps/content-factory/episodes/produce.py --channel finance --ep 1 --no-voice
    python apps/content-factory/episodes/produce.py --channel aitech --probe-only

Voice bật khi có NARRATION_FILE hoặc ELEVENLABS_API_KEY+ELEVEN_VOICE_ID (xem narration.py);
không có thì tự chạy nhạc nền. KHÔNG tự publish YouTube.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.abspath(os.path.join(_HERE, "..", "..", "..")), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from libs.video import list_keys, ffmpeg_available  # noqa: E402
import factory  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Produce 1 episode cho 1 kênh")
    ap.add_argument("--channel", help="key kênh (xem --list)")
    ap.add_argument("--ep", type=int, default=1, help="số tập")
    ap.add_argument("--title", default="", help="tiêu đề tập")
    ap.add_argument("--out", default=None, help="thư mục output")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--no-srt", action="store_true")
    ap.add_argument("--no-thumb", action="store_true")
    ap.add_argument("--limit-scenes", type=int, default=None, help="giới hạn số cảnh (test)")
    ap.add_argument("--list", action="store_true", help="liệt kê kênh")
    ap.add_argument("--probe-only", action="store_true", help="chỉ kiểm tra nguồn ảnh")
    args = ap.parse_args(argv)

    if args.list:
        for k in list_keys():
            print(k)
        return 0
    if args.probe_only:
        print(json.dumps(factory.check_resources(), ensure_ascii=False, indent=2))
        return 0
    if not args.channel:
        ap.error("cần --channel (hoặc --list / --probe-only)")
    if not ffmpeg_available():
        print("ffmpeg/ffprobe không có — không thể render.", file=sys.stderr)
        return 2

    req = factory.EpisodeRequest(
        channel_key=args.channel, episode_no=args.ep, title=args.title,
        music=not args.no_music, want_voice=not args.no_voice,
        want_srt=not args.no_srt, want_thumb=not args.no_thumb,
        limit_scenes=args.limit_scenes,
    )
    rep = factory.make_episode(req, out_dir=args.out)
    r = rep["render"]
    qa = rep["qa"]
    print(f"✅ [{rep['channel']}] {rep['brand']} — {rep['title']}")
    print(f"   MP4: {r['path']} ({r.get('duration')}s, {r.get('size')}B, "
          f"voice={r.get('narration')}, music={r.get('music')})")
    if rep.get("srt"):
        print(f"   SRT: {rep['srt']}")
    if rep.get("thumbnail"):
        print(f"   Thumb: {rep['thumbnail']}")
    print(f"   QA: {'PASS' if qa['passed'] else 'FAIL'} "
          f"({sum(c['ok'] for c in qa['checks'])}/{len(qa['checks'])})")
    print(f"   YouTube: {rep['youtube_dry_run']['status']} — KHÔNG tự publish")
    print(f"   manifest: {rep['manifest']}")
    return 0 if qa["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
