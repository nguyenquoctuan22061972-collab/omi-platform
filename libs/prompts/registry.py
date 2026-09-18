"""Prompt Registry (PRD-009 B): quản lý + version hoá prompt theo 8 loại."""
from __future__ import annotations

from typing import Dict, List

CATEGORIES = [
    "youtube_long",
    "shorts",
    "tiktok",
    "facebook",
    "seo",
    "thumbnail",
    "veo3",
    "vertex",
]

# Prompt mặc định (v1) — template gọn; tùy biến/nâng version sau. KHÔNG chứa secret.
_DEFAULTS: Dict[str, str] = {
    "youtube_long": "Viết kịch bản video YouTube dài về {topic}, có hook, thân bài, CTA.",
    "shorts": "Viết kịch bản Shorts <60s về {topic}, hook 3s đầu.",
    "tiktok": "Viết kịch bản TikTok về {topic}, trend-friendly, CTA ngắn.",
    "facebook": "Viết post Facebook về {topic}, ngắn gọn, kèm câu hỏi tương tác.",
    "seo": "Tạo tiêu đề + mô tả + tags SEO cho nội dung về {topic}.",
    "thumbnail": "Mô tả concept thumbnail cho {topic}: bố cục, text overlay, cảm xúc.",
    "veo3": "Prompt sinh video (Veo3) cho cảnh: {topic}, mô tả chuyển động/ánh sáng.",
    "vertex": "Prompt tối ưu cho Vertex AI về {topic}, rõ input/output.",
}


class PromptRegistry:
    def __init__(self):
        # store[category] = list các version (index+1 = version)
        self._store: Dict[str, List[str]] = {c: [] for c in CATEGORIES}
        for c, tpl in _DEFAULTS.items():
            self._store[c].append(tpl)

    def categories(self) -> List[str]:
        return list(CATEGORIES)

    def add_version(self, category: str, template: str) -> int:
        if category not in self._store:
            raise KeyError(f"category không hợp lệ: {category}")
        self._store[category].append(template)
        return len(self._store[category])  # version number

    def latest_version(self, category: str) -> int:
        return len(self._store[category])

    def get(self, category: str, version: int | None = None) -> str:
        if category not in self._store:
            raise KeyError(f"category không hợp lệ: {category}")
        versions = self._store[category]
        if not versions:
            raise KeyError(f"chưa có prompt cho: {category}")
        v = version or len(versions)
        if v < 1 or v > len(versions):
            raise IndexError(f"version {v} ngoài phạm vi (1..{len(versions)})")
        return versions[v - 1]

    def render(self, category: str, version: int | None = None, **kwargs) -> str:
        return self.get(category, version).format(**kwargs)
