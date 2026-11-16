"""AFFOS KPI Query Foundation (WP-D05-01) — READ-ONLY aggregation over existing data.

Reuses (never forks/mutates): money_status, provenance, economics. Works with any repo exposing
.query(sql, params) (the SQLite TEST adapter in tests; PostgresRepository in prod). SELECT-only:
this module issues no INSERT/UPDATE/DELETE and changes no engine, schema, or enum.

Design decisions (CEO-approved D1–D6):
  - D4: Recognized Revenue counts ONLY provenance.is_real rows (production-verified). This is STRICTER
    than attribution.totals (which sums all CONFIRMED regardless of data_state), so the filter is
    applied HERE, reusing provenance.is_real — attribution is left unchanged.
  - D2: no Impact-specific filter; PRODUCTION_SOURCES is used as-is (so Impact production rows count).
  - D3: Margin is N/A (not 0.0) when the revenue denominator is 0 — handled in this layer.
  - Currency-aware: multiple currencies are never collapsed into one number.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Dict, Optional

_CORE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (_CORE, os.path.join(_CORE, "economics")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import money_status   # noqa: E402
import provenance     # noqa: E402
import economics      # noqa: E402

NA = "N/A"
_COST_PARAMS = ("ai_cost", "content_cost", "infrastructure_cost", "advertising_cost")


def _commissions(repo, currency: Optional[str]):
    rows = repo.query(
        "SELECT amount, status, currency, source, source_record_id, data_state, is_verified "
        "FROM commissions")
    if currency:
        rows = [r for r in rows if (r.get("currency") or "VND") == currency]
    return rows


def revenue_breakdown(repo, currency: Optional[str] = None) -> Dict:
    """Per-currency revenue split into recognized / unverified / simulated.

    recognized = Σ(confirmed − refund) over is_real rows ONLY (D4).
    unverified = LIVE rows that are not is_real (revenue_label == UNVERIFIED_REVENUE).
    simulated  = TEST/DRY_RUN/SEEDED rows (revenue_label == SIMULATED_REVENUE).
    Missing/invalid provenance rows are reported, never silently summed.
    """
    rows = _commissions(repo, currency)
    recognized = defaultdict(float)
    unverified = defaultdict(float)
    simulated = defaultdict(float)
    invalid_provenance = []  # reported, not summed

    for r in rows:
        cur = r.get("currency") or "VND"
        amt = float(r.get("amount") or 0)
        if not r.get("source") or not r.get("source_record_id") or r.get("data_state") is None:
            invalid_provenance.append(r)
            continue
        signed = amt if money_status.is_confirmed(r.get("status")) else (
            -amt if money_status.is_refund(r.get("status")) else None)
        if signed is None:
            continue  # pending/declined/cancelled/rejected: never revenue
        if provenance.is_real(r):                       # D4: recognized = production-verified only
            recognized[cur] += signed
        else:
            label = provenance.revenue_label(r.get("data_state"))
            if label == "SIMULATED_REVENUE":            # TEST / DRY_RUN / SEEDED
                simulated[cur] += signed
            else:                                       # UNVERIFIED_REVENUE, or PRODUCTION label
                unverified[cur] += signed               # that failed is_real -> not recognized


    currencies = sorted(set(recognized) | set(unverified) | set(simulated))
    return {
        "currencies": currencies,
        "recognized": {c: round(recognized[c], 2) for c in currencies},
        "unverified": {c: round(unverified[c], 2) for c in currencies},
        "simulated": {c: round(simulated[c], 2) for c in currencies},
        "invalid_provenance_count": len(invalid_provenance),
    }


def _single_currency_recognized(bd: Dict, currency: Optional[str]):
    """Return (currency, recognized_amount) for a single-currency view, or (None, None) if mixed."""
    recog = bd["recognized"]
    curs = [c for c in bd["currencies"] if recog.get(c)]  # currencies with nonzero recognized
    if currency:
        return currency, recog.get(currency, 0.0)
    if len(curs) > 1:
        return None, None            # mixed currency — refuse a single figure (currency-aware rule)
    cur = curs[0] if curs else (bd["currencies"][0] if bd["currencies"] else None)
    return cur, (recog.get(cur, 0.0) if cur else 0.0)


def financial_kpis(repo, ai_cost: float = 0.0, content_cost: float = 0.0,
                   infrastructure_cost: float = 0.0, advertising_cost: float = 0.0,
                   currency: Optional[str] = None) -> Dict:
    """Revenue / Cost / Net Profit / Margin for a single currency (ROI/Cash/Net Cash Flow DEFERRED).

    Advertising cost is reused from the expenses table (same source as attribution), plus any
    advertising_cost passed in. Margin is N/A when recognized revenue is 0 (D3).
    """
    bd = revenue_breakdown(repo, currency)
    cur, recognized = _single_currency_recognized(bd, currency)

    if cur is None and recognized is None:
        return {"mixed_currency": True, "currencies": bd["currencies"],
                "by_currency_recognized": bd["recognized"],
                "revenue": None, "roi": None, "cash": None, "net_cash_flow": None,
                "note": "multiple currencies with recognized revenue — pass currency= or apply FX",
                "read_only": True}

    ad_from_exp = repo.query(
        "SELECT COALESCE(SUM(amount),0) AS s FROM expenses WHERE category='advertising'")[0]["s"] or 0
    econ = economics.contribution_profit(
        recognized, ai_cost=ai_cost, content_cost=content_cost,
        infrastructure_cost=infrastructure_cost, advertising_cost=advertising_cost + ad_from_exp)

    profit = econ["contribution_profit"]
    margin = NA if not recognized else round(profit / recognized, 4)   # D3: N/A, not 0.0

    return {
        "currency": cur,
        "recognized_revenue": round(recognized, 2),
        "unverified_revenue": bd["unverified"].get(cur, 0.0) if cur else 0.0,
        "simulated_revenue": bd["simulated"].get(cur, 0.0) if cur else 0.0,
        "total_cost": econ["total_cost"],
        "net_profit": round(profit, 2),
        "margin": margin,
        "roi": None,              # DEFERRED — not computed/displayed (gate pending)
        "cash": None,             # DEFERRED — WP-R02
        "net_cash_flow": None,    # DEFERRED — WP-R02
        "cost_breakdown": econ["breakdown"],
        "invalid_provenance_count": bd["invalid_provenance_count"],
        "mixed_currency": False,
        "read_only": True,
    }
