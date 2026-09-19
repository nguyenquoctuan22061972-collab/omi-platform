"""YouTube Runtime (PRD-010 D): upload adapter, thumbnail binding, metadata builder,
playlist mapper, schedule abstraction. DRY-RUN — KHÔNG upload thật. Credential từ env.
"""
from __future__ import annotations

from typing import Dict, List, Mapping

REQUIRED_ENV = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]

# category → playlist env key (map placeholder; giá trị thật từ env).
PLAYLIST_ENV = {
    "finance": "YT_PLAYLIST_FINANCE",
    "tech": "YT_PLAYLIST_TECH",
    "inspire": "YT_PLAYLIST_INSPIRE",
    "default": "YT_PLAYLIST_DEFAULT",
}


def build_metadata(title: str, description: str = "", tags: List[str] | None = None,
                   privacy: str = "private") -> Dict:
    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": (tags or [])[:15],
        "privacyStatus": privacy if privacy in ("private", "unlisted", "public") else "private",
    }


class YouTubeRuntime:
    def __init__(self, env: Mapping[str, str] | None = None):
        self.env = env or {}

    def is_configured(self) -> bool:
        return all(self.env.get(k) for k in REQUIRED_ENV)

    def playlist_for(self, category: str) -> str:
        key = PLAYLIST_ENV.get(category, PLAYLIST_ENV["default"])
        return self.env.get(key, "")

    def bind_thumbnail(self, video_ref: str, thumbnail_ref: str) -> Dict:
        return {"video": video_ref, "thumbnail": thumbnail_ref, "status": "dry-run"}

    def schedule(self, publish_at_iso: str) -> Dict:
        return {"publishAt": publish_at_iso, "status": "scheduled-dry-run"}

    def upload(self, video_ref: str, metadata: Dict, category: str = "default",
               thumbnail_ref: str = "", publish_at: str = "") -> Dict:
        """DRY-RUN upload — trả kế hoạch, KHÔNG gọi YouTube API."""
        return {
            "status": "dry-run",
            "configured": self.is_configured(),
            "video": video_ref,
            "metadata": metadata,
            "playlist_env": PLAYLIST_ENV.get(category, PLAYLIST_ENV["default"]),
            "thumbnail": self.bind_thumbnail(video_ref, thumbnail_ref) if thumbnail_ref else None,
            "schedule": self.schedule(publish_at) if publish_at else None,
            "note": "chưa upload thật — gắn credential + hiện thực API để bật",
        }
