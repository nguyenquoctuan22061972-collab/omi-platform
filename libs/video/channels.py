"""Registry 10 kênh của hệ thống (template dùng chung 1 engine, đổi brand/handle/màu).

Nguồn: danh sách "Tên kênh chính thức đã xác nhận" của CEO. Mỗi kênh là một preset cho
`VideoRenderer` + metadata YouTube; engine render/voice/srt/thumbnail giữ nguyên, chỉ
tham số theo kênh thay đổi. `yt_category` map sang `libs/youtube` PLAYLIST_ENV
(finance/tech/inspire/default) để chọn playlist khi publish (vẫn dry-run mặc định).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Channel:
    key: str                       # định danh ngắn dùng ở CLI (--channel)
    gmail: str                     # tài khoản gmail quản lý
    brand: str                     # tên kênh hiển thị
    handle: str                    # @handle
    niche: str                     # chủ đề
    accent: Tuple[int, int, int]   # màu nhấn (RGB) theo nhận diện kênh
    yt_category: str               # finance | tech | inspire | default
    lang: str = "vi"               # ngôn ngữ nội dung/voiceover
    voice_hint: str = "warm, calm, inspirational"  # gợi ý chất giọng cho TTS

    def __repr__(self) -> str:
        return f"<Channel {self.key} {self.brand} {self.handle}>"


# Thứ tự theo bảng CEO đã chốt (1..10).
CHANNELS: List[Channel] = [
    Channel("heartrise", "nguyenquoctuan22061972", "HeartRise Stories",
            "@HeartRiseStories", "Cảm hứng / Inspire", (255, 173, 94), "inspire",
            voice_hint="warm, gentle, inspirational"),
    Channel("aitech", "tuannqai", "AITechDaily",
            "@AITechDaily", "AI & Technology", (94, 196, 255), "tech",
            voice_hint="clear, confident, modern"),
    Channel("risestory", "quoctuan933us", "RiseStoryChronicles",
            "@RiseStoryChronicles", "Real Stories", (240, 180, 100), "inspire",
            voice_hint="narrative, heartfelt"),
    Channel("health", "nguyentuan576933", "HealthWellnessDaily",
            "@HealthWellnessDaily", "Health & Wellness", (120, 210, 150), "default",
            voice_hint="calm, reassuring"),
    Channel("finance", "nguyenquoctuan1369", "FinanceFreedomPro",
            "@FinanceFreedomPro", "Finance", (212, 175, 55), "finance",
            voice_hint="authoritative, grounded"),
    Channel("travel", "nguyenquoctuankiengiang", "HiddenAsia Travel",
            "@HiddenAsiaTravel", "Travel", (80, 200, 190), "default",
            voice_hint="bright, curious"),
    Channel("marketing", "marketing.quoctuan", "GrowthHack Hub",
            "@GrowthHackHub", "Marketing & Business", (170, 130, 255), "default",
            voice_hint="energetic, sharp"),
    Channel("selfdev", "marketing.quoctuan1", "LevelUp Life",
            "@LevelUpLife", "Self Development", (90, 170, 255), "inspire",
            voice_hint="motivating, upbeat"),
    Channel("mystery", "mkt.quoctuan", "WorldMysteriesDaily",
            "@WorldMysteriesDaily", "History & Mystery", (180, 120, 220), "default",
            voice_hint="intriguing, cinematic"),
    Channel("wisdom", "nqtuananbinh", "LifeWisdomDaily",
            "@LifeWisdomDaily", "Spiritual & Wisdom", (230, 200, 120), "default",
            voice_hint="serene, contemplative"),
]

CHANNEL_BY_KEY: Dict[str, Channel] = {c.key: c for c in CHANNELS}


def get_channel(key: str) -> Channel:
    key = (key or "").strip().lower()
    if key not in CHANNEL_BY_KEY:
        raise KeyError(
            f"kênh '{key}' không có. Hợp lệ: {', '.join(CHANNEL_BY_KEY)}"
        )
    return CHANNEL_BY_KEY[key]


def list_keys() -> List[str]:
    return [c.key for c in CHANNELS]
