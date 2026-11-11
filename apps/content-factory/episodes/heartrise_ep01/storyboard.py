"""Kịch bản (storyboard) cho HeartRise Stories — TẬP 01: "Ngày Con Tim Thức Dậy".

Kênh #1 (niche Cảm hứng / Inspire), handle @HeartRiseStories. Nội dung tiếng Việt,
cung bậc: Hook → Gục ngã → Bước ngoặt → Vươn dậy → Hành động → Thông điệp → Kết.

Mỗi cảnh khai báo NHIỀU url ứng viên (nhiều nguồn) để fallback khi một domain bị chặn.
Toàn bộ asset là ảnh miễn phí (Pexels/Unsplash/Pixabay License).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

EPISODE_ID = "heartrise_ep01"
CHANNEL = "HeartRise Stories"
HANDLE = "@HeartRiseStories"
TITLE = "Ngày Con Tim Thức Dậy"

# Metadata để build mô tả YouTube (KHÔNG tự publish — dry-run ở libs/youtube).
YT_TITLE = "Ngày Con Tim Thức Dậy | HeartRise Stories — Tập 01"
YT_DESCRIPTION = (
    "Có những buổi sáng ta thức dậy mà thấy lòng trống rỗng. Nhưng mặt trời chưa bao "
    "giờ hỏi xin phép để mọc lên. Tập mở màn của HeartRise Stories — nơi mỗi vết nứt "
    "trong tim là nơi ánh sáng tìm được đường vào.\n\n"
    "🎧 Âm nhạc: nhạc nền ambient gốc (tổng hợp).\n"
    "🖼️ Hình ảnh: tư liệu miễn phí (Pexels / Unsplash / Pixabay License).\n\n"
    "#HeartRise #CâuChuyệnCảmHứng #ĐộngLực #ChữaLành"
)
YT_TAGS = [
    "cảm hứng", "động lực", "chữa lành", "câu chuyện cuộc sống",
    "heartrise", "inspire", "vươn lên", "tích cực", "bình yên",
]


@dataclass
class SceneSpec:
    key: str
    duration: float
    kind: str
    zoom: str
    align: str
    kraft: str
    title: str
    subtitle: str
    urls: List[str] = field(default_factory=list)


# Các url đã được kiểm chứng tải được (200 + JPEG thật) từ 3 nguồn.
STORYBOARD: List[SceneSpec] = [
    SceneSpec(
        key="intro", duration=7.0, kind="intro", zoom="in", align="center",
        kraft="HeartRise Stories · Tập 01",
        title="Ngày Con Tim\nThức Dậy",
        subtitle="Một câu chuyện nhỏ cho những trái tim đang mỏi mệt",
        urls=[
            "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80",
            "https://images.pexels.com/photos/355747/pexels-photo-355747.jpeg?auto=compress&cs=tinysrgb&w=1920",
        ],
    ),
    SceneSpec(
        key="hook", duration=9.0, kind="story", zoom="in", align="bottom",
        kraft="",
        title="Có những buổi sáng…",
        subtitle="ta thức dậy mà thấy lòng mình trống rỗng,\nnhư căn phòng vừa có người bước ra.",
        urls=[
            "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1920&q=80",
            "https://images.pexels.com/photos/417074/pexels-photo-417074.jpeg?auto=compress&cs=tinysrgb&w=1920",
        ],
    ),
    SceneSpec(
        key="struggle", duration=9.0, kind="story", zoom="out", align="bottom",
        kraft="",
        title="Giấc mơ từng rực cháy",
        subtitle="nay chỉ còn là tro tàn\ncủa những lần ta đã gục ngã.",
        urls=[
            "https://images.unsplash.com/photo-1476231682828-37e571bc172f?w=1920&q=80",
            "https://cdn.pixabay.com/photo/2016/11/29/05/45/astronomy-1867616_1280.jpg",
        ],
    ),
    SceneSpec(
        key="turn", duration=9.0, kind="quote", zoom="in", align="center",
        kraft="Bước ngoặt",
        title="“Mặt trời chưa bao giờ\nhỏi xin phép để mọc lên.”",
        subtitle="Và bạn cũng vậy.",
        urls=[
            "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1920&q=80",
            "https://images.pexels.com/photos/355747/pexels-photo-355747.jpeg?auto=compress&cs=tinysrgb&w=1920",
        ],
    ),
    SceneSpec(
        key="rise", duration=9.0, kind="story", zoom="in", align="bottom",
        kraft="",
        title="Mỗi vết nứt trong tim",
        subtitle="là nơi ánh sáng\ntìm được đường để bước vào.",
        urls=[
            "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1920&q=80",
            "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&q=80",
        ],
    ),
    SceneSpec(
        key="action", duration=8.0, kind="story", zoom="out", align="bottom",
        kraft="",
        title="Hôm nay, chỉ cần một bước",
        subtitle="Nhỏ thôi.\nNhưng là bước của chính bạn.",
        urls=[
            "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&q=80",
            "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1920&q=80",
        ],
    ),
    SceneSpec(
        key="message", duration=9.0, kind="quote", zoom="in", align="center",
        kraft="Thông điệp",
        title="“Con tim không vỡ\nđể kết thúc —",
        subtitle="nó vỡ để mở rộng hơn.”",
        urls=[
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1920&q=80",
            "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920&q=80",
        ],
    ),
    SceneSpec(
        key="outro", duration=8.0, kind="outro", zoom="out", align="center",
        kraft="Hẹn gặp ở Tập 02",
        title="Nếu câu chuyện này\nchạm đến bạn…",
        subtitle="hãy ở lại cùng HeartRise.\nĐăng ký để con tim được thức dậy mỗi tuần.",
        urls=[
            "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920&q=80",
            "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80",
        ],
    ),
]


def total_runtime(crossfade: float = 0.8) -> float:
    raw = sum(s.duration for s in STORYBOARD)
    return raw - crossfade * (len(STORYBOARD) - 1)
