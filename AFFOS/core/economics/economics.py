"""AFFOS Economics (PRD-017). Contribution Profit + Opportunity Score. Pure, no network.

Contribution Profit = Revenue − (commission adj + refunds + AI + content + infra + advertising).
Opportunity Score = Demand×Trend×Conversion×EPC×Commission×ContentFit ÷ Competition ÷ ProductionCost.
"""
from __future__ import annotations

from typing import Dict

COST_KEYS = ["commission_adjustments", "refunds", "ai_cost", "content_cost",
             "infrastructure_cost", "advertising_cost"]


def contribution_profit(revenue: float, **costs) -> Dict:
    breakdown = {k: float(costs.get(k, 0) or 0) for k in COST_KEYS}
    total_cost = sum(breakdown.values())
    profit = float(revenue) - total_cost
    margin = (profit / revenue) if revenue else 0.0
    return {"revenue": float(revenue), "total_cost": round(total_cost, 6),
            "contribution_profit": round(profit, 6), "margin": round(margin, 4),
            "breakdown": breakdown}


def opportunity_score(demand: float, trend: float, conversion: float, epc: float,
                      commission: float, content_fit: float,
                      competition: float, production_cost: float) -> float:
    denom = float(competition) * float(production_cost)
    if denom <= 0:
        raise ValueError("competition và production_cost phải > 0")
    num = demand * trend * conversion * epc * commission * content_fit
    return round(num / denom, 6)


def ai_revenue_ratio(ai_cost: float, revenue: float) -> Dict:
    # P0-3: zero (or negative) revenue is NOT "healthy" — there is simply no revenue data
    # to judge cost efficiency. Report NO_REVENUE_DATA and healthy=False, never a false green.
    if not revenue or float(revenue) <= 0:
        return {"ai_cost": float(ai_cost), "revenue": float(revenue or 0),
                "ratio_pct": None, "status": "NO_REVENUE_DATA", "healthy": False}
    ratio = ai_cost / revenue
    return {"ai_cost": float(ai_cost), "revenue": float(revenue),
            "ratio_pct": round(ratio * 100, 1), "status": "OK",
            "healthy": ratio <= 0.30}   # cảnh báo khi AI/Revenue > 30%
