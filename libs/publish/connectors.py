"""Publish connectors (PRD-009 G): YouTube, TikTok, Facebook, Telegram. Dry-run."""
from __future__ import annotations

from typing import Dict, List, Mapping

# connector → env cần để "configured".
CONNECTORS: Dict[str, List[str]] = {
    "youtube": ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
    "tiktok": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
    "facebook": ["FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"],
    "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
}


class PublishConnector:
    def __init__(self, name: str, env: Mapping[str, str] | None = None):
        if name not in CONNECTORS:
            raise KeyError(f"connector không hợp lệ: {name}")
        self.name = name
        self.required_env = CONNECTORS[name]
        env = env or {}
        self.config = {k: env.get(k, "") for k in self.required_env}

    def is_configured(self) -> bool:
        return all(self.config.values())

    def publish(self, content: Dict) -> Dict:
        """DRY-RUN: KHÔNG publish thật. Trả mô tả hành động."""
        return {
            "status": "dry-run",
            "connector": self.name,
            "configured": self.is_configured(),
            "would_publish": {k: content.get(k) for k in ("title", "kind") if k in content},
            "note": "chưa publish thật — gắn credential + bật production",
        }


def get_connector(name: str, env: Mapping[str, str] | None = None) -> PublishConnector:
    return PublishConnector(name, env or {})
