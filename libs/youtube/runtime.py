"""YouTube Runtime (PRD-010 D): upload adapter, thumbnail binding, metadata builder,
playlist mapper, schedule abstraction.

Mặc định DRY-RUN (không upload). `upload(..., live=True)` bật đường upload THẬT qua YouTube
Data API v3 (OAuth refresh-token → resumable upload) — chỉ chạy khi đã cấu hình credential
và caller chủ động bật. CỔNG AN TOÀN: không bao giờ tự đặt public — privacy "public" bị hạ
xuống "private" trừ khi YT_ALLOW_PUBLIC=1. Credential đọc từ env, không hardcode.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from typing import Dict, List, Mapping

REQUIRED_ENV = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]

# YouTube numeric categoryId: 22 = People & Blogs, 27 = Education, 24 = Entertainment.
CATEGORY_ID = {"finance": "22", "tech": "28", "inspire": "22", "default": "22"}

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
               "?uploadType=resumable&part=snippet,status")

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
               thumbnail_ref: str = "", publish_at: str = "", live: bool = False) -> Dict:
        """Mặc định DRY-RUN. `live=True` + đã cấu hình → upload THẬT (private mặc định)."""
        plan = {
            "status": "dry-run",
            "configured": self.is_configured(),
            "video": video_ref,
            "metadata": metadata,
            "playlist_env": PLAYLIST_ENV.get(category, PLAYLIST_ENV["default"]),
            "thumbnail": self.bind_thumbnail(video_ref, thumbnail_ref) if thumbnail_ref else None,
            "schedule": self.schedule(publish_at) if publish_at else None,
            "note": "chưa upload thật — gắn credential + live=True để bật",
        }
        if not live:
            return plan
        if not self.is_configured():
            plan["note"] = "live=True nhưng thiếu credential (YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN)"
            return plan
        return self._live_upload(video_ref, metadata, category, thumbnail_ref, publish_at)

    # ---------- đường upload THẬT (guarded) ----------
    def _ssl_ctx(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ca = self.env.get("CCR_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
        if os.path.exists(ca):
            try:
                ctx.load_verify_locations(ca)
            except Exception:
                pass
        return ctx

    def access_token(self) -> str:
        """Đổi refresh-token lấy access-token (OAuth 2.0)."""
        data = urllib.parse.urlencode({
            "client_id": self.env.get("YOUTUBE_CLIENT_ID", ""),
            "client_secret": self.env.get("YOUTUBE_CLIENT_SECRET", ""),
            "refresh_token": self.env.get("YOUTUBE_REFRESH_TOKEN", ""),
            "grant_type": "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(_TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=30, context=self._ssl_ctx()) as r:
            tok = json.loads(r.read().decode("utf-8"))
        if "access_token" not in tok:
            raise RuntimeError("không lấy được access_token từ refresh_token")
        return tok["access_token"]

    def _enforce_privacy(self, metadata: Dict) -> Dict:
        """Cổng an toàn: không bao giờ tự public trừ khi YT_ALLOW_PUBLIC=1."""
        md = dict(metadata)
        if md.get("privacyStatus") == "public" and self.env.get("YT_ALLOW_PUBLIC") != "1":
            md["privacyStatus"] = "private"
            md["_privacy_downgraded"] = True
        return md

    def _live_upload(self, video_ref: str, metadata: Dict, category: str,
                     thumbnail_ref: str, publish_at: str) -> Dict:
        md = self._enforce_privacy(metadata)
        status: Dict = {"privacyStatus": md.get("privacyStatus", "private")}
        if publish_at:
            status["publishAt"] = publish_at
            status["privacyStatus"] = "private"   # scheduled phải private tới giờ phát
        body = json.dumps({
            "snippet": {
                "title": md.get("title", ""),
                "description": md.get("description", ""),
                "tags": md.get("tags", []),
                "categoryId": CATEGORY_ID.get(category, CATEGORY_ID["default"]),
            },
            "status": status,
        }).encode("utf-8")

        token = self.access_token()
        with open(video_ref, "rb") as f:
            payload = f.read()

        # 1) khởi tạo phiên resumable
        init = urllib.request.Request(_UPLOAD_URL, data=body, method="POST")
        init.add_header("Authorization", f"Bearer {token}")
        init.add_header("Content-Type", "application/json; charset=UTF-8")
        init.add_header("X-Upload-Content-Type", "video/*")
        init.add_header("X-Upload-Content-Length", str(len(payload)))
        with urllib.request.urlopen(init, timeout=60, context=self._ssl_ctx()) as r:
            session_url = r.headers.get("Location")
        if not session_url:
            raise RuntimeError("không nhận được resumable session URL")

        # 2) PUT toàn bộ bytes
        put = urllib.request.Request(session_url, data=payload, method="PUT")
        put.add_header("Content-Type", "video/*")
        put.add_header("Content-Length", str(len(payload)))
        with urllib.request.urlopen(put, timeout=600, context=self._ssl_ctx()) as r:
            resource = json.loads(r.read().decode("utf-8"))

        return {
            "status": "uploaded",
            "video_id": resource.get("id"),
            "privacyStatus": status["privacyStatus"],
            "privacy_downgraded": md.get("_privacy_downgraded", False),
            "thumbnail_pending": bool(thumbnail_ref),
            "note": "upload thật xong; thumbnail/playlist set qua call riêng nếu cần",
        }
