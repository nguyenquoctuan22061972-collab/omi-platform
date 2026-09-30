"""AFFOS Real-Commerce Proof (PRD-017 / CTO review).

VERIFIED chỉ khi toàn chuỗi có bằng chứng production Awin đã verify. Ngược lại NOT YET VERIFIED.
"""
from __future__ import annotations

import os
import sys
from typing import Dict

sys.path.insert(0, os.path.dirname(__file__))
import provenance  # noqa: E402


def real_commerce_proof(repo) -> Dict:
    reasons = []
    conv = repo.query("SELECT data_state, is_verified, source FROM conversion_events")
    comm = repo.query("SELECT data_state, is_verified, source FROM commissions")

    def all_prod(rows):
        return bool(rows) and all(provenance.is_real(r) for r in rows)

    conv_ok = all_prod(conv)
    comm_ok = all_prod(comm)
    if not conv:
        reasons.append("không có conversion")
    elif not conv_ok:
        reasons.append("conversion chưa PRODUCTION_VERIFIED từ awin_production")
    if not comm:
        reasons.append("không có commission")
    elif not comm_ok:
        reasons.append("commission chưa PRODUCTION_VERIFIED từ awin_production")

    verified = conv_ok and comm_ok
    return {"status": "VERIFIED" if verified else "NOT YET VERIFIED",
            "report_line": f"REAL COMMERCE PROOF: {'VERIFIED' if verified else 'NOT YET VERIFIED'}",
            "reasons": reasons}
