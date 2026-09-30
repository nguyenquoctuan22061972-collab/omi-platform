"""AFFOS Attribution (PRD-017). Nối click → conversion → commission → revenue → profit.

Reuse: economics.contribution_profit. Đọc từ Repo (data_access). Thuần SQL/agg, không network.
"""
from __future__ import annotations

import os
import sys
from typing import Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "economics"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import economics  # noqa: E402
import provenance  # noqa: E402


def per_campaign(repo) -> Dict:
    """Tổng hợp theo campaign: clicks, conversions, revenue(commission), EPC, CR."""
    rows = repo.query("""
        SELECT c.id AS campaign_id,
               COUNT(DISTINCT ce.id) AS clicks,
               COUNT(DISTINCT cv.id) AS conversions,
               COALESCE(SUM(co.amount),0) AS revenue
        FROM campaigns c
        LEFT JOIN tracking_links tl ON tl.campaign_id = c.id
        LEFT JOIN click_events ce ON ce.tracking_link_id = tl.id
        LEFT JOIN conversion_events cv ON cv.click_event_id = ce.id
        LEFT JOIN commissions co ON co.conversion_event_id = cv.id AND co.status='confirmed'
        GROUP BY c.id
    """)
    out = {}
    for r in rows:
        clicks = r["clicks"] or 0
        out[r["campaign_id"]] = {
            "clicks": clicks, "conversions": r["conversions"] or 0,
            "revenue": round(r["revenue"] or 0, 2),
            "epc": round((r["revenue"] or 0) / clicks, 4) if clicks else 0.0,
            "cr": round((r["conversions"] or 0) / clicks, 4) if clicks else 0.0,
        }
    return out


def totals(repo, ai_cost: float = 0.0, content_cost: float = 0.0,
           infrastructure_cost: float = 0.0, advertising_cost: float = 0.0) -> Dict:
    revenue = repo.query("SELECT COALESCE(SUM(amount),0) AS s FROM commissions WHERE status='confirmed'")[0]["s"] or 0
    refunds = repo.query("SELECT COALESCE(SUM(amount),0) AS s FROM commissions WHERE status='refunded'")[0]["s"] or 0
    ad_from_exp = repo.query("SELECT COALESCE(SUM(amount),0) AS s FROM expenses WHERE category='advertising'")[0]["s"] or 0
    profit = economics.contribution_profit(
        revenue, refunds=refunds, ai_cost=ai_cost, content_cost=content_cost,
        infrastructure_cost=infrastructure_cost, advertising_cost=advertising_cost + ad_from_exp)
    # Trạng thái dữ liệu: verified chỉ khi MỌI commission là PRODUCTION_VERIFIED + is_verified.
    rows = repo.query("SELECT data_state, is_verified FROM commissions")
    verified = bool(rows) and all(r["data_state"] == "PRODUCTION_VERIFIED" and int(r["is_verified"] or 0) == 1 for r in rows)
    data_state = "PRODUCTION_VERIFIED" if verified else (rows[0]["data_state"] if rows else "DRY_RUN")
    return {"revenue": round(revenue, 2), "refunds": round(refunds, 2),
            "data_state": data_state, "revenue_label": provenance.revenue_label(data_state),
            "is_verified": verified, **profit}
