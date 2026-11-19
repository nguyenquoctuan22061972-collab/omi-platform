"""Sinh kịch bản (script) theo TỪNG NICHE — mỗi kênh một nội dung riêng (không trùng).

Giữ cung bậc chuẩn 8 cảnh (Intro → Hook → Gục ngã → Bước ngoặt → Vươn dậy → Hành động →
Thông điệp → Kết) nhưng lời thoại + chữ trên màn hình được viết riêng cho từng chủ đề.
Hình ảnh dùng pool cinematic chung (THEME_URLS trong factory) — nhất quán thị giác.

Nguồn offline, deterministic, chạy-được-ngay. Có chỗ nối LLM thật qua `generate_with`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class Beat:
    key: str
    kind: str           # intro | story | quote | outro
    zoom: str
    align: str
    kraft: str
    title: str
    subtitle: str
    theme: str          # key ảnh trong pool (factory.THEME_URLS)


# Khung cố định 8 cảnh: (key, kind, zoom, align, theme). Chữ điền theo niche.
_STRUCTURE: List[Tuple[str, str, str, str, str]] = [
    ("intro",    "intro", "in",  "center", "sunrise horizon calm"),
    ("hook",     "story", "in",  "bottom", "foggy sea boat"),
    ("struggle", "story", "out", "bottom", "long road dusk"),
    ("turn",     "quote", "in",  "center", "sun rays mountain"),
    ("rise",     "story", "in",  "bottom", "forest light path"),
    ("action",   "story", "out", "bottom", "walking trail green"),
    ("message",  "quote", "in",  "center", "peak summit sky"),
    ("outro",    "outro", "out", "center", "lake mountain calm"),
]

# Nhãn chủ đề tiếng Việt (dùng cho intro) theo channel.niche.
NICHE_LABEL: Dict[str, str] = {
    "AI & Technology": "AI & Công nghệ",
    "Real Stories": "Câu chuyện có thật",
    "Health & Wellness": "Sức khỏe & An lành",
    "Finance": "Tự do tài chính",
    "Travel": "Du ký châu Á",
    "Marketing & Business": "Marketing & Kinh doanh",
    "Self Development": "Phát triển bản thân",
    "History & Mystery": "Lịch sử & Bí ẩn",
    "Spiritual & Wisdom": "Minh triết & Tâm linh",
    "Cảm hứng / Inspire": "Cảm hứng",
}

# Mỗi niche: 8 bộ (kraft, title, subtitle) khớp 8 cảnh. {brand}/{tap}/{label} thay ở generate.
_SCRIPTS: Dict[str, List[Tuple[str, str, str]]] = {
    "AI & Technology": [
        ("{brand} · {tap}", "Trí Tuệ\nCủa Ngày Mai", "Công nghệ không thay thế bạn — nó khuếch đại điều bạn vốn có"),
        ("", "Thế giới đang đổi thay…", "mỗi ngày một công cụ mới,\nvà ta sợ mình bị bỏ lại phía sau."),
        ("", "Nhưng công cụ chỉ là công cụ", "giá trị thật nằm ở\nngười biết đặt câu hỏi đúng."),
        ("Sự thật", "“AI không lấy việc của bạn —\nngười biết dùng AI mới làm.”", "Vậy hãy là người đó."),
        ("", "Mỗi dòng code, mỗi câu hỏi", "là một bước bạn đi trước\nchính mình của hôm qua."),
        ("", "Hôm nay, học một điều mới", "Nhỏ thôi.\nNhưng cộng dồn thành tương lai."),
        ("Thông điệp", "“Tương lai thuộc về\nngười không ngừng học.”", "Và đó chính là bạn."),
        ("Hẹn gặp ở tập sau", "Nếu điều này hữu ích…", "hãy ở lại cùng {brand}.\nMỗi ngày một bước tới tương lai."),
    ],
    "Real Stories": [
        ("{brand} · {tap}", "Những Người\nĐã Vươn Lên", "Câu chuyện có thật về những con người bình thường, phi thường"),
        ("", "Ai cũng có một đêm tối", "khi mọi cánh cửa\ndường như đóng lại."),
        ("", "Họ từng ngã rất sâu", "mất mát, hoài nghi,\nvà cả niềm tin vào chính mình."),
        ("Bước ngoặt", "“Điều làm nên con người\nkhông phải cú ngã —”", "mà là lần họ đứng dậy."),
        ("", "Từ đáy vực, họ bước lên", "từng bước nhỏ,\nkhông ai thấy, trừ chính họ."),
        ("", "Và một ngày, họ nhìn lại", "nhận ra: vực sâu ấy\nđã dạy họ cách bay."),
        ("Thông điệp", "“Câu chuyện của bạn\nchưa kết thúc.”", "Chương hay nhất còn ở phía trước."),
        ("Hẹn gặp ở tập sau", "Nếu câu chuyện này\ntiếp sức cho bạn…", "hãy ở lại cùng {brand}.\nMỗi tuần một hành trình vươn lên."),
    ],
    "Health & Wellness": [
        ("{brand} · {tap}", "Lắng Nghe\nCơ Thể", "Sức khỏe & an lành bắt đầu từ những điều nhỏ mỗi ngày"),
        ("", "Ta chạy mãi không ngừng", "đến mức quên mất\ncơ thể cũng cần được nghỉ."),
        ("", "Mệt mỏi không phải yếu đuối", "đó là lời nhắc\nhãy chậm lại một nhịp."),
        ("Bước ngoặt", "“Chăm sóc bản thân\nkhông ích kỷ —”", "đó là nền móng của mọi điều."),
        ("", "Một giấc ngủ đủ, một hơi thở sâu", "cơ thể bắt đầu\ntự chữa lành."),
        ("", "Hôm nay, uống thêm một ly nước", "đi bộ mười phút.\nTử tế với chính mình."),
        ("Thông điệp", "“Cơ thể khỏe mạnh\nlà ngôi nhà của tâm an.”", "Hãy giữ gìn nó."),
        ("Hẹn gặp ở tập sau", "Nếu điều này\nnhắc bạn nghỉ ngơi…", "hãy ở lại cùng {brand}.\nMỗi tuần một thói quen an lành."),
    ],
    "Finance": [
        ("{brand} · {tap}", "Tự Do\nTài Chính", "Tiền không mua được bình yên, nhưng tư duy đúng thì có"),
        ("", "Nhiều người kiếm được tiền", "nhưng chẳng mấy ai\nthật sự tự do."),
        ("", "Nợ nần, lo toan, so sánh", "khiến ta chạy mãi\nmà chẳng tới đâu."),
        ("Bước ngoặt", "“Giàu không phải có nhiều —\nmà là cần ít hơn.”", "Tự do bắt đầu từ đó."),
        ("", "Mỗi đồng để dành hôm nay", "là một viên gạch\nxây nên tự do mai sau."),
        ("", "Hôm nay, ghi lại chi tiêu", "Chi tiết nhỏ ấy\nthay đổi cả cuộc đời."),
        ("Thông điệp", "“Hãy để tiền\nlàm việc cho bạn.”", "Chứ không ngược lại."),
        ("Hẹn gặp ở tập sau", "Nếu điều này\nmở ra một hướng đi…", "hãy ở lại cùng {brand}.\nMỗi tuần một bước tới tự do."),
    ],
    "Travel": [
        ("{brand} · {tap}", "Những Miền\nChưa Đặt Tên", "Du ký châu Á — nơi mỗi con đường kể một câu chuyện"),
        ("", "Có những sớm mai", "ta thức dậy\nvà khao khát được đi."),
        ("", "Nhưng nỗi sợ giữ ta lại", "sợ lạc đường,\nsợ điều chưa biết."),
        ("Bước ngoặt", "“Chân trời không xa —\nchỉ là ta chưa bước.”", "Hãy bước đi."),
        ("", "Mỗi vùng đất mới", "dạy ta một điều\nsách vở không có."),
        ("", "Hôm nay, lên một kế hoạch", "Một chuyến đi nhỏ\ncũng đủ đổi cách ta nhìn đời."),
        ("Thông điệp", "“Thế giới là cuốn sách —\nkẻ ở yên chỉ đọc một trang.”", "Hãy lật sang trang mới."),
        ("Hẹn gặp ở tập sau", "Nếu nơi này\ngọi tên bạn…", "hãy ở lại cùng {brand}.\nMỗi tuần một miền đất mới."),
    ],
    "Marketing & Business": [
        ("{brand} · {tap}", "Xây Điều\nNgười Khác Cần", "Marketing & kinh doanh — nghệ thuật tạo ra giá trị thật"),
        ("", "Ai cũng muốn bán được hàng", "nhưng ít ai hỏi:\nmình giải quyết vấn đề gì?"),
        ("", "Chạy theo xu hướng", "khiến ta kiệt sức\nmà thương hiệu vẫn mờ nhạt."),
        ("Bước ngoặt", "“Đừng tìm khách cho sản phẩm —\nlàm sản phẩm cho khách.”", "Mọi thứ đổi từ đó."),
        ("", "Mỗi khách hàng được lắng nghe", "là một người\nsẽ kể về bạn."),
        ("", "Hôm nay, hỏi một khách hàng", "họ thật sự cần gì.\nCâu trả lời là vàng."),
        ("Thông điệp", "“Thương hiệu lớn\nđược xây bằng niềm tin.”", "Mỗi ngày một chút."),
        ("Hẹn gặp ở tập sau", "Nếu điều này\ngiúp bạn tăng trưởng…", "hãy ở lại cùng {brand}.\nMỗi tuần một chiến lược thật."),
    ],
    "Self Development": [
        ("{brand} · {tap}", "Phiên Bản\nTốt Hơn", "Phát triển bản thân — mỗi ngày tiến một phần trăm"),
        ("", "Ta mơ về thay đổi lớn", "rồi bỏ cuộc\nvì nó quá xa vời."),
        ("", "Nhưng thay đổi lớn", "luôn bắt đầu\ntừ một thói quen nhỏ."),
        ("Bước ngoặt", "“Bạn không cần giỏi hơn ai —\nchỉ cần hơn chính mình hôm qua.”", "Mỗi ngày một phần trăm."),
        ("", "Một trang sách, một lần dậy sớm", "từng việc nhỏ\nnặn nên con người bạn."),
        ("", "Hôm nay, làm điều bạn trì hoãn", "Chỉ năm phút thôi.\nKỷ luật bắt đầu từ đó."),
        ("Thông điệp", "“Thành công\nlà tổng của những việc nhỏ lặp lại.”", "Hãy bắt đầu hôm nay."),
        ("Hẹn gặp ở tập sau", "Nếu điều này\ntiếp lửa cho bạn…", "hãy ở lại cùng {brand}.\nMỗi tuần một cú nâng cấp bản thân."),
    ],
    "History & Mystery": [
        ("{brand} · {tap}", "Những Bí Ẩn\nChưa Lời Đáp", "Lịch sử & bí ẩn — nơi quá khứ thì thầm những câu chuyện"),
        ("", "Lịch sử đầy khoảng trống", "những điều\nchưa ai giải thích nổi."),
        ("", "Càng đào sâu, càng nhiều câu hỏi", "sự thật đôi khi\nkỳ lạ hơn truyền thuyết."),
        ("Bước ngoặt", "“Mỗi bí ẩn\nlà một cánh cửa —”", "chờ người đủ tò mò mở ra."),
        ("", "Sau mỗi tàn tích", "là một nền văn minh\ntừng rực rỡ như ta."),
        ("", "Hôm nay, đặt một câu hỏi", "về điều bạn tưởng đã biết.\nTri thức bắt đầu từ đó."),
        ("Thông điệp", "“Quá khứ không chết —\nnó đang kể chuyện.”", "Hãy lắng nghe."),
        ("Hẹn gặp ở tập sau", "Nếu bí ẩn này\nkhiến bạn tò mò…", "hãy ở lại cùng {brand}.\nMỗi tuần một câu chuyện chưa kể."),
    ],
    "Spiritual & Wisdom": [
        ("{brand} · {tap}", "Sự Tĩnh Lặng\nBên Trong", "Minh triết & tâm linh — tìm bình yên giữa đời vội vã"),
        ("", "Giữa ồn ào cuộc sống", "ta đánh mất\ntiếng nói bên trong."),
        ("", "Càng tìm kiếm bên ngoài", "ta càng xa\nđiều vốn đã có sẵn."),
        ("Bước ngoặt", "“Bình yên không ở nơi đến —\nnó ở trong cách ta đi.”", "Hãy trở về bên trong."),
        ("", "Một phút tĩnh lặng mỗi ngày", "đủ để nghe\ntrái tim mình thì thầm."),
        ("", "Hôm nay, ngồi yên một lát", "Hít thở. Buông bỏ.\nChỉ hiện diện, thế thôi."),
        ("Thông điệp", "“Khi tâm an,\nthế giới cũng dịu lại.”", "Bình yên bắt đầu từ bạn."),
        ("Hẹn gặp ở tập sau", "Nếu những lời này\nchạm đến bạn…", "hãy ở lại cùng {brand}.\nMỗi tuần một khoảnh khắc an nhiên."),
    ],
}


def _fallback(brand: str, niche: str) -> List[Tuple[str, str, str]]:
    label = NICHE_LABEL.get(niche, niche)
    return [
        ("{brand} · {tap}", "Khởi Đầu\nMới", f"Một câu chuyện nhỏ về {label.lower()} cho hôm nay"),
        ("", "Có những ngày…", "ta bước đi mà thấy lòng mình chênh vênh."),
        ("", "Điều ta mong mỏi", "nhiều khi tới chậm hơn\nsức ta có thể chờ."),
        ("Bước ngoặt", "“Ánh sáng không đợi\nbóng tối cho phép.”", "Và bạn cũng vậy."),
        ("", "Mỗi lần ngã xuống", "là một lần ta học được\ncách đứng vững hơn."),
        ("", "Hôm nay, một bước nhỏ", "Chậm cũng được.\nMiễn là bước của chính bạn."),
        ("Thông điệp", "“Hành trình nghìn dặm\nbắt đầu từ một hơi thở.”", "Hãy bắt đầu."),
        ("Hẹn gặp ở tập sau", "Nếu điều này chạm đến bạn…", "hãy ở lại cùng {brand}.\nĐăng ký để không bỏ lỡ."),
    ]


def generate(brand: str, niche: str, episode_no: int, title: str,
             generate_with: Optional[Callable[..., List[Beat]]] = None) -> List[Beat]:
    """Trả 8 Beat theo niche. Ưu tiên generate_with (LLM) nếu hợp lệ; ngược lại dùng
    bộ kịch bản riêng của niche; không có thì fallback chung."""
    if generate_with is not None:
        try:
            beats = generate_with(brand=brand, niche=niche,
                                   episode_no=episode_no, title=title)
            if beats and all(isinstance(b, Beat) for b in beats):
                return beats
        except Exception:
            pass
    rows = _SCRIPTS.get(niche) or _fallback(brand, niche)
    tap = f"Tập {episode_no:02d}"
    beats: List[Beat] = []
    for (key, kind, zoom, align, theme), (kraft, t, sub) in zip(_STRUCTURE, rows):
        fmt = lambda s: s.replace("{brand}", brand).replace("{tap}", tap)
        beats.append(Beat(key, kind, zoom, align, fmt(kraft), fmt(t), fmt(sub), theme))
    return beats


def script_text(beats: List[Beat]) -> str:
    """Ghép lời đọc (narration) từ các beat — bỏ ký tự trang trí, nối câu mạch lạc."""
    parts: List[str] = []
    for b in beats:
        for seg in (b.title, b.subtitle):
            seg = (seg or "").replace("\n", " ").strip().strip("“”\"").strip()
            if seg:
                parts.append(seg)
    return " … ".join(parts)
