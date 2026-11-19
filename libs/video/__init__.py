"""Video production lib (additive, PRD-009 E "video" stage made real).

Reuses stdlib + ffmpeg + Pillow + numpy already present in the runtime.
KHÔNG đổi kiến trúc PRD001–013: đây là lib mới, các module cũ không bị sửa.
Pipeline `content-factory` có thể dùng renderer này qua `runner` injectable sẵn có
(không phải fork pipeline).
"""
from __future__ import annotations

from .sources import (
    AssetSource,
    SOURCES,
    probe_sources,
    pick_source,
    download_asset,
    download_first,
    AssetUnavailable,
)
from .renderer import Scene, VideoRenderer, ffmpeg_available, xfade_offsets
from .channels import Channel, CHANNELS, get_channel, list_keys
from .narration import (
    NarrationSpec,
    NarrationProvider,
    SilentNarration,
    FileNarration,
    ElevenLabsNarration,
    from_env as narration_from_env,
)
from .subtitles import srt_from_scenes, write_srt, scene_windows

__all__ = [
    "AssetSource",
    "SOURCES",
    "probe_sources",
    "pick_source",
    "download_asset",
    "download_first",
    "AssetUnavailable",
    "Scene",
    "VideoRenderer",
    "ffmpeg_available",
    "xfade_offsets",
    "Channel",
    "CHANNELS",
    "get_channel",
    "list_keys",
    "NarrationSpec",
    "NarrationProvider",
    "SilentNarration",
    "FileNarration",
    "ElevenLabsNarration",
    "narration_from_env",
    "srt_from_scenes",
    "write_srt",
    "scene_windows",
]
