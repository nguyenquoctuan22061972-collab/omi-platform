"""Module tagging (PRD-001 §9.3 "AI gắn tag").

Stub xác định (rule-based) để test được và làm điểm cắm cho AI thật sau này.
Gắn tag theo kênh nguồn và từ khoá trong tin nhắn.
"""
from __future__ import annotations

from typing import List


# Từ khoá → tag (ánh xạ tối giản, mở rộng/thay bằng model AI sau).
_KEYWORD_TAGS = {
    "giá": "pricing",
    "price": "pricing",
    "mua": "intent-buy",
    "order": "intent-buy",
    "đặt": "intent-buy",
    "lỗi": "support",
    "hỏng": "support",
    "support": "support",
    "khiếu nại": "complaint",
}


def suggest_tags(message: str = "", channel: str = "") -> List[str]:
    """Trả về danh sách tag gợi ý (không trùng, ổn định thứ tự)."""
    tags: List[str] = []
    if channel:
        ch = f"channel:{channel.strip().lower().replace(' ', '-')}"
        tags.append(ch)
    low = (message or "").lower()
    for kw, tag in _KEYWORD_TAGS.items():
        if kw in low and tag not in tags:
            tags.append(tag)
    return tags
