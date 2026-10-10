"""AFFOS Real-Commerce Proof (PRD-017 / MONEY integrity).

VERIFIED only when the whole chain carries verified production provenance. Otherwise NOT YET
VERIFIED. P0-6: proof can be scoped to a campaign so stale/unrelated rows never falsify a new
experiment's proof. P0-7: reports attribution linkage (whether clicks carry a tracking_link_id).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(__file__))
import provenance  # noqa: E402


def real_commerce_proof(repo, campaign_id: Optional[str] = None) -> Dict:
    reasons = []
    if campaign_id:
        conv = repo.query(
            "SELECT cv.data_state, cv.is_verified, cv.source FROM conversion_events cv "
            "JOIN click_events ce ON cv.click_event_id = ce.id "
            "JOIN tracking_links tl ON ce.tracking_link_id = tl.id WHERE tl.campaign_id = ?",
            (campaign_id,))
        comm = repo.query(
            "SELECT co.data_state, co.is_verified, co.source FROM commissions co "
            "JOIN conversion_events cv ON co.conversion_event_id = cv.id "
            "JOIN click_events ce ON cv.click_event_id = ce.id "
            "JOIN tracking_links tl ON ce.tracking_link_id = tl.id WHERE tl.campaign_id = ?",
            (campaign_id,))
        link_rows = repo.query(
            "SELECT ce.tracking_link_id AS tl FROM conversion_events cv "
            "LEFT JOIN click_events ce ON cv.click_event_id = ce.id "
            "LEFT JOIN tracking_links t ON ce.tracking_link_id = t.id WHERE t.campaign_id = ?",
            (campaign_id,))
    else:
        conv = repo.query("SELECT data_state, is_verified, source FROM conversion_events")
        comm = repo.query("SELECT data_state, is_verified, source FROM commissions")
        link_rows = repo.query(
            "SELECT ce.tracking_link_id AS tl FROM conversion_events cv "
            "LEFT JOIN click_events ce ON cv.click_event_id = ce.id")

    def all_prod(rows):
        return bool(rows) and all(provenance.is_real(r) for r in rows)

    conv_ok = all_prod(conv)
    comm_ok = all_prod(comm)
    if not conv:
        reasons.append("không có conversion" + (f" cho campaign {campaign_id}" if campaign_id else ""))
    elif not conv_ok:
        reasons.append("conversion chưa PRODUCTION_VERIFIED từ nguồn production")
    if not comm:
        reasons.append("không có commission" + (f" cho campaign {campaign_id}" if campaign_id else ""))
    elif not comm_ok:
        reasons.append("commission chưa PRODUCTION_VERIFIED từ nguồn production")

    # P0-7: attribution is end-to-end only if every in-scope click carries a tracking_link_id.
    attribution_linked = bool(link_rows) and all((r.get("tl") or "") != "" for r in link_rows)
    if conv and not attribution_linked:
        reasons.append("attribution bị giới hạn: click_events thiếu tracking_link_id (không nối network click)")

    verified = conv_ok and comm_ok and attribution_linked
    return {"status": "VERIFIED" if verified else "NOT YET VERIFIED",
            "report_line": f"REAL COMMERCE PROOF: {'VERIFIED' if verified else 'NOT YET VERIFIED'}",
            "scope": campaign_id or "ALL",
            "attribution_linked": attribution_linked,
            "reasons": reasons}
