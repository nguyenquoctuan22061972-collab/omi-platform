"""Nối ContentPipeline (PRD-009 E) với engine render thật (libs/video + episodes/factory).

ContentPipeline.advance(runner) gọi `runner(stage)` cho từng stage và lưu artifact. Module
này cung cấp một runner ánh xạ stage → công việc thật:

    topic/research/script → text kịch bản
    thumbnail            → đường dẫn thumbnail (hoặc "planned" khi render=False)
    video                → render MP4 thật qua factory.make_episode (cache lại report)
    qa                   → kết quả QA
    publish              → kế hoạch YouTube DRY-RUN (không publish)

`render=False` (mặc định cho test/CI không có ffmpeg): mỗi stage trả chuỗi "planned" nên
pipeline vẫn chạy trọn mà không render. `render=True`: stage video gọi engine thật.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_EPISODES = os.path.join(_ROOT, "apps", "content-factory", "episodes")
for _p in (_ROOT, _EPISODES):
    if _p not in sys.path:
        sys.path.insert(0, _p)


class EpisodeRunner:
    """Runner trạng-thái dùng cho ContentPipeline. Render 1 lần ở stage 'video', cache."""

    def __init__(self, channel_key: str, episode_no: int = 1, title: str = "",
                 out_dir: Optional[str] = None, render: bool = False,
                 music: bool = True, voice: bool = True):
        self.channel_key = channel_key
        self.episode_no = episode_no
        self.title = title
        self.out_dir = out_dir
        self.render = render
        self.music = music
        self.voice = voice
        self.report: Optional[dict] = None

    def _ensure_render(self) -> dict:
        if self.report is not None:
            return self.report
        import factory  # episodes/factory.py
        req = factory.EpisodeRequest(
            channel_key=self.channel_key, episode_no=self.episode_no,
            title=self.title, music=self.music, want_voice=self.voice,
        )
        self.report = factory.make_episode(req, out_dir=self.out_dir)
        return self.report

    def __call__(self, stage: str) -> str:
        if stage in ("topic", "research", "script"):
            return f"[{self.channel_key}] script/{stage} ep{self.episode_no:02d}"
        if not self.render:
            return f"[{self.channel_key}] {stage} planned (render=off)"
        rep = self._ensure_render()
        if stage == "thumbnail":
            return rep.get("thumbnail", "thumbnail")
        if stage == "video":
            return rep["render"]["path"]
        if stage == "qa":
            return "QA:PASS" if rep.get("qa", {}).get("passed") else "QA:FAIL"
        if stage == "publish":
            return f"youtube:{rep['youtube_dry_run']['status']}"
        return f"[{self.channel_key}] {stage}"


def run_episode_pipeline(channel_key: str, episode_no: int = 1, title: str = "",
                         out_dir: Optional[str] = None, render: bool = False) -> dict:
    """Chạy trọn ContentPipeline cho 1 tập, dùng EpisodeRunner. Trả kết quả pipeline."""
    sys.path.insert(0, os.path.join(_ROOT, "apps", "content-factory", "pipeline"))
    from pipeline import ContentPipeline  # type: ignore
    runner = EpisodeRunner(channel_key, episode_no, title, out_dir, render=render)
    pipe = ContentPipeline(topic=f"{channel_key} ep{episode_no:02d}")
    result = pipe.run_all(runner)
    result["episode_report"] = runner.report
    return result
