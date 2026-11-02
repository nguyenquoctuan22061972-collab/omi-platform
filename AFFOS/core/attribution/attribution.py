"""AFFOS Attribution (PRD-017 / MONEY integrity). click → conversion → commission → revenue.

Reuse: economics.contribution_profit, money_status (canonical), provenance. Reads from Repo.
P0 fixes:
  - canonical status matching (APPROVED/CONFIRMED recognized; REFUNDED/REVERSED reversal).
  - net recognized revenue = Σ confirmed − Σ refund, with NO second refund subtraction.
  - currency-aware: never sum across currencies; mixed currencies return a per-currency map.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "economics"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import economics       # noqa: E402
import provenance      # noqa: E402
import money_status    # noqa: E402


def per_campaign(repo) -> Dict:
    """Theo campaign: clicks, conversions, revenue(confirmed commission), EPC, CR."""
    rows = repo.query(f"""
        SELECT c.id AS campaign_id,
               COUNT(DISTINCT ce.id) AS clicks,
               COUNT(DISTINCT cv.id) AS conversions,
               COALESCE(SUM(CASE WHEN {money_status.SQL_CONFIRMED.replace('status','co.status')}
                                 THEN co.amount ELSE 0 END),0) AS revenue
        FROM campaigns c
        LEFT JOIN tracking_links tl ON tl.campaign_id = c.id
        LEFT JOIN click_events ce ON ce.tracking_link_id = tl.id
        LEFT JOIN conversion_events cv ON cv.click_event_id = ce.id
        LEFT JOIN commissions co ON co.conversion_event_id = cv.id
        GROUP BY c.id
    """)
    out = {}
    for r in rows:
        clicks = r["clicks"] or 0
        rev = r["revenue"] or 0
        out[r["campaign_id"]] = {
            "clicks": clicks, "conversions": r["conversions"] or 0,
            "revenue": round(rev, 2),
            "epc": round(rev / clicks, 4) if clicks else 0.0,
            "cr": round((r["conversions"] or 0) / clicks, 4) if clicks else 0.0,
        }
    return out


def _data_state(rows) -> tuple:
    verified = bool(rows) and all(
        r["data_state"] == "PRODUCTION_VERIFIED" and int(r["is_verified"] or 0) == 1 for r in rows)
    ds = "PRODUCTION_VERIFIED" if verified else (rows[0]["data_state"] if rows else "DRY_RUN")
    return ds, verified


def totals(repo, ai_cost: float = 0.0, content_cost: float = 0.0,
           infrastructure_cost: float = 0.0, advertising_cost: float = 0.0,
           currency: Optional[str] = None) -> Dict:
    rows = repo.query("SELECT amount, status, currency, data_state, is_verified FROM commissions")
    if currency:
        rows = [r for r in rows if (r.get("currency") or "VND") == currency]

    gross, refund = defaultdict(float), defaultdict(float)
    for r in rows:
        cur = r.get("currency") or "VND"
        amt = float(r.get("amount") or 0)
        if money_status.is_confirmed(r.get("status")):
            gross[cur] += amt
        elif money_status.is_refund(r.get("status")):
            refund[cur] += amt
    currencies = sorted(set(gross) | set(refund))
    ds, verified = _data_state(rows)

    # P0-4: refuse to collapse multiple currencies into one number.
    if len(currencies) > 1:
        by_cur = {c: {"gross_revenue": round(gross[c], 2), "refunds": round(refund[c], 2),
                      "revenue": round(gross[c] - refund[c], 2)} for c in currencies}
        return {"revenue": None, "mixed_currency": True, "currencies": currencies,
                "by_currency": by_cur, "data_state": ds,
                "revenue_label": provenance.revenue_label(ds), "is_verified": verified,
                "note": "multiple currencies present — pass currency= or convert with FX before summing"}

    cur = currencies[0] if currencies else (currency or "VND")
    gross_rev = gross.get(cur, 0.0)
    refunds = refund.get(cur, 0.0)
    net_rev = gross_rev - refunds                      # P0-2: refund folded in ONCE, not re-subtracted
    ad_from_exp = repo.query("SELECT COALESCE(SUM(amount),0) AS s FROM expenses WHERE category='advertising'")[0]["s"] or 0
    profit = economics.contribution_profit(
        net_rev, ai_cost=ai_cost, content_cost=content_cost,
        infrastructure_cost=infrastructure_cost, advertising_cost=advertising_cost + ad_from_exp)
    return {"revenue": round(net_rev, 2), "gross_revenue": round(gross_rev, 2),
            "refunds": round(refunds, 2), "currency": cur, "mixed_currency": False,
            "data_state": ds, "revenue_label": provenance.revenue_label(ds),
            "is_verified": verified, **profit}
