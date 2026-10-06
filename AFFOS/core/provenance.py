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
CONVERSION_TYPES = {"AWIN_PRODUCTION_CONVERSION", "SEEDED_CONVERSION"}
REVENUE_LABELS = {"PRODUCTION_REVENUE", "SIMULATED_REVENUE"}

PRODUCTION_SOURCES = {"awin_production", "impact_production"}   # nguồn production được duyệt REAL


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
    return "PRODUCTION_REVENUE" if data_state in ("LIVE", "PRODUCTION_VERIFIED") else "SIMULATED_REVENUE"


def click_type(data_state: str, network_reported: bool = False) -> str:
    if data_state in ("LIVE", "PRODUCTION_VERIFIED"):
        return "NETWORK_REPORTED_CLICK" if network_reported else "AFFOS_TRACKED_CLICK"
    return "SEEDED_CLICK"


def conversion_type(data_state: str) -> str:
    return "AWIN_PRODUCTION_CONVERSION" if data_state in ("LIVE", "PRODUCTION_VERIFIED") else "SEEDED_CONVERSION"
