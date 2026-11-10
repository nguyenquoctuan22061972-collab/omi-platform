"""AFFOS Provenance & Data-State model (PRD-017 / CTO review).

KHÔNG BAO GIỜ gọi dữ liệu là REAL trừ khi verified từ môi trường production (Awin).
Mọi record tài chính/sự kiện phải mang: source, source_record_id, data_state, currency,
fetched_at, is_verified.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

# Vòng đời trạng thái dữ liệu (không được nhảy cóc sang PRODUCTION_VERIFIED nếu chưa verify).
DATA_STATES = ["TEST", "DRY_RUN", "SEEDED", "LIVE", "PRODUCTION_VERIFIED"]
NON_REAL_STATES = {"TEST", "DRY_RUN", "SEEDED"}   # tuyệt đối không gắn nhãn REAL

# Phân loại event (bắt buộc phân biệt seeded vs production).
CLICK_TYPES = {"AFFOS_TRACKED_CLICK", "NETWORK_REPORTED_CLICK", "SEEDED_CLICK"}
CONVERSION_TYPES = {"AWIN_PRODUCTION_CONVERSION", "IMPACT_PRODUCTION_CONVERSION", "SEEDED_CONVERSION"}
REVENUE_LABELS = {"PRODUCTION_REVENUE", "UNVERIFIED_REVENUE", "SIMULATED_REVENUE"}

# Chỉ nguồn production ĐÃ ĐƯỢC CEO phê duyệt mới được is_real()==True.
# Impact ("impact_production") CỐ Ý KHÔNG nằm ở đây cho đến khi CEO phê duyệt RIÊNG Impact LIVE.
# => mọi record Impact (kể cả production-transport, verified) đều is_real()==False. Việc thêm
#    "impact_production" vào đây là quyết định có kiểm soát của CEO/CTO, không phải mặc định.
PRODUCTION_SOURCES = {"awin_production"}   # nguồn production được duyệt REAL (AWIN only, hiện tại)


def provenance(source: str, source_record_id: str, data_state: str,
               currency: str = "VND", fetched_at: Optional[str] = None,
               is_verified: bool = False) -> Dict:
    if data_state not in DATA_STATES:
        raise ValueError(f"data_state không hợp lệ: {data_state}")
    if is_verified and data_state != "PRODUCTION_VERIFIED":
        raise ValueError("is_verified=True chỉ hợp lệ khi data_state=PRODUCTION_VERIFIED")
    return {"source": source, "source_record_id": source_record_id,
            "data_state": data_state, "currency": currency,
            "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat(),
            "is_verified": 1 if is_verified else 0}


def is_real(rec: Dict) -> bool:
    """REAL = verified từ production. Seeded/dry-run/test KHÔNG BAO GIỜ real."""
    return (rec.get("data_state") == "PRODUCTION_VERIFIED"
            and int(rec.get("is_verified", 0)) == 1
            and rec.get("source") in PRODUCTION_SOURCES)


def revenue_label(data_state: str) -> str:
    # P0-5: PRODUCTION_REVENUE only when the chain is PRODUCTION_VERIFIED. LIVE is fetched-but-
    # unverified → UNVERIFIED_REVENUE (not REAL yet). TEST/DRY_RUN/SEEDED → SIMULATED_REVENUE.
    if data_state == "PRODUCTION_VERIFIED":
        return "PRODUCTION_REVENUE"
    if data_state == "LIVE":
        return "UNVERIFIED_REVENUE"
    return "SIMULATED_REVENUE"


def click_type(data_state: str, network_reported: bool = False) -> str:
    if data_state in ("LIVE", "PRODUCTION_VERIFIED"):
        return "NETWORK_REPORTED_CLICK" if network_reported else "AFFOS_TRACKED_CLICK"
    return "SEEDED_CLICK"


# Nhãn conversion production theo ĐÚNG nguồn mạng, lấy từ provenance "source" (không suy từ data_state).
_PRODUCTION_CONVERSION_BY_SOURCE = {
    "awin_production": "AWIN_PRODUCTION_CONVERSION",
    "impact_production": "IMPACT_PRODUCTION_CONVERSION",
}


def conversion_type(data_state: str, source: str = "") -> str:
    """Phân loại conversion theo nguồn mạng. TEST/DRY_RUN/SEEDED → SEEDED_CONVERSION.

    LIVE/PRODUCTION_VERIFIED → nhãn theo `source`: awin_production → AWIN_PRODUCTION_CONVERSION,
    impact_production → IMPACT_PRODUCTION_CONVERSION. Một production state có source lạ/trống KHÔNG
    được coi là AWIN — trả về SEEDED_CONVERSION, để không mạng mới nào bị gắn nhầm nhãn AWIN.
    (Nhãn này chỉ cho biết NGUỒN/loại sự kiện; tư cách REAL do is_real() quyết định riêng.)
    """
    if data_state not in ("LIVE", "PRODUCTION_VERIFIED"):
        return "SEEDED_CONVERSION"
    return _PRODUCTION_CONVERSION_BY_SOURCE.get(source, "SEEDED_CONVERSION")
