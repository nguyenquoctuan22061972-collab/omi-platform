"""Sinh kịch bản (script) template cho một tập — nguồn offline, deterministic.

Cung bậc chuẩn kênh faceless cảm hứng: Intro → Hook → Gục ngã → Bước ngoặt → Vươn dậy
→ Hành động → Thông điệp → Kết. Mỗi beat có eyebrow/title/subtitle + gợi ý hình (theme).

Đây là nguồn mặc định để pipeline chạy-được-ngay (không cần LLM). Có thể thay bằng LLM
thật qua `generate_with` (nhận callable trả cùng cấu trúc) — chỗ nối cho libs/ai_router.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class Beat:
    key: str
    kind: str           # intro | story | quote | outro
    zoom: str
    align: str
    kraft: str
    title: str
    subtitle: str
    theme: str          # từ khoá hình ảnh (gợi ý chọn asset)


def _default_beats(brand: str, niche: str, episode_no: int, title: str) -> List[Beat]:
    tap = f"Tập {episode_no:02d}"
    return [
        Beat("intro", "intro", "in", "center", f"{brand} · {tap}",
             title, f"Một câu chuyện nhỏ về {niche.lower()} cho hôm nay",
             "sunrise horizon calm"),
        Beat("hook", "story", "in", "bottom", "",
             "Có những ngày…", "ta bước đi mà thấy lòng mình chênh vênh,\n"
             "như con thuyền lạc mất bến bờ.", "foggy sea boat"),
        Beat("struggle", "story", "out", "bottom", "",
             "Điều ta mong mỏi", "nhiều khi tới chậm hơn\nsức ta có thể chờ.",
             "long road dusk"),
        Beat("turn", "quote", "in", "center", "Bước ngoặt",
             "“Ánh sáng không đợi\nbóng tối cho phép.”", "Và bạn cũng vậy.",
             "sun rays mountain"),
        Beat("rise", "story", "in", "bottom", "",
             "Mỗi lần ngã xuống", "là một lần ta học được\ncách đứng vững hơn.",
             "forest light path"),
        Beat("action", "story", "out", "bottom", "",
             "Hôm nay, một bước nhỏ", "Chậm cũng được.\nMiễn là bước của chính bạn.",
             "walking trail green"),
        Beat("message", "quote", "in", "center", "Thông điệp",
             "“Hành trình nghìn dặm\nbắt đầu từ một hơi thở.”", "Hãy bắt đầu.",
             "peak summit sky"),
        Beat("outro", "outro", "out", "center", "Hẹn gặp tập sau",
             f"Nếu điều này chạm đến bạn…", f"hãy ở lại cùng {brand}.\n"
             "Đăng ký để không bỏ lỡ câu chuyện kế tiếp.", "lake mountain calm"),
    ]


def generate(brand: str, niche: str, episode_no: int, title: str,
             generate_with: Optional[Callable[..., List[Beat]]] = None) -> List[Beat]:
    """Trả list Beat. Mặc định dùng template; nếu truyền generate_with (vd LLM) thì ưu
    tiên kết quả hợp lệ của nó, ngược lại fallback template."""
    if generate_with is not None:
        try:
            beats = generate_with(brand=brand, niche=niche,
                                   episode_no=episode_no, title=title)
            if beats and all(isinstance(b, Beat) for b in beats):
                return beats
        except Exception:
            pass
    return _default_beats(brand, niche, episode_no, title)


def script_text(beats: List[Beat]) -> str:
    """Ghép lời đọc (narration) từ các beat — bỏ ký tự trang trí, nối câu mạch lạc."""
    parts: List[str] = []
    for b in beats:
        for seg in (b.title, b.subtitle):
            seg = (seg or "").replace("\n", " ").strip().strip("“”\"").strip()
            if seg:
                parts.append(seg)
    return " … ".join(parts)
