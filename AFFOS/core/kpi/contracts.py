"""AFFOS KPI Contracts (WP-D05-01) — declarative KPI specifications.

Pure data + consistency assertions. No DB access, no network, no mutation. Each contract records:
  id, name, definition, formula, source (reused engine), currency rule, data_state rule,
  missing-data rule, status.

The contracts reference the EXISTING provenance vocabulary (imported read-only) and assert, at import
time, that this module introduces no new data_state or revenue label — a guard against drift.
"""
from __future__ import annotations

import os
import sys
from typing import Dict

_CORE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)
import provenance  # noqa: E402  (reuse canonical vocabulary — read-only)

# Sentinel for a metric whose denominator/condition makes it undefined (never silently 0).
NA = "N/A"

# Status of each KPI in WP-D05-01.
ACTIVE = "ACTIVE"
DEFERRED = "DEFERRED"


def _c(id, name, definition, formula, source, currency_rule, data_state_rule,
       missing_data_rule, status) -> Dict:
    return {"id": id, "name": name, "definition": definition, "formula": formula,
            "source": source, "currency_rule": currency_rule, "data_state_rule": data_state_rule,
            "missing_data_rule": missing_data_rule, "status": status}


KPI_CONTRACTS: Dict[str, Dict] = {
    "recognized_revenue": _c(
        "recognized_revenue", "Recognized Revenue",
        "Confirmed commission net of refunds, counted only for production-verified records.",
        "sum(confirmed.amount) - sum(refund.amount) over rows where provenance.is_real(row)",
        "money_status + provenance.is_real (reuse)",
        "per-currency; never aggregate across currencies without approved FX",
        "only is_real rows (PRODUCTION_VERIFIED + is_verified=1 + source in PRODUCTION_SOURCES)",
        "missing -> excluded, never coerced to 0; invalid provenance reported, not summed",
        ACTIVE),
    "unverified_revenue": _c(
        "unverified_revenue", "Unverified Revenue",
        "Revenue from LIVE-but-not-verified records; reported separately, NOT recognized.",
        "sum over rows with revenue_label == UNVERIFIED_REVENUE",
        "provenance.revenue_label (reuse)",
        "per-currency", "data_state == LIVE and not is_real",
        "reported separately; never added into Recognized Revenue", ACTIVE),
    "simulated_revenue": _c(
        "simulated_revenue", "Simulated Revenue",
        "Revenue from TEST/DRY_RUN/SEEDED records; reported separately, NOT recognized.",
        "sum over rows with revenue_label == SIMULATED_REVENUE",
        "provenance.revenue_label (reuse)",
        "per-currency", "data_state in {TEST, DRY_RUN, SEEDED}",
        "reported separately; never added into Recognized Revenue", ACTIVE),
    "total_cost": _c(
        "total_cost", "Total Cost",
        "Sum of cost components used for Net Profit (commission adj, refunds, AI, content, infra, ads).",
        "sum(economics.COST_KEYS)",
        "economics.contribution_profit (reuse)",
        "same currency as revenue; costs carry their own source",
        "n/a (cost is provenance-tagged at source)",
        "missing cost component -> excluded, never coerced to 0 silently", ACTIVE),
    "net_profit": _c(
        "net_profit", "Net Profit",
        "Recognized Revenue minus Total Costs.",
        "recognized_revenue - total_cost",
        "economics.contribution_profit (reuse)",
        "single currency only (mixed -> per-currency, no single figure)",
        "derived from recognized revenue (is_real)",
        "incomplete inputs must not produce a falsely precise total", ACTIVE),
    "margin": _c(
        "margin", "Margin",
        "Net Profit divided by Recognized Revenue.",
        "net_profit / recognized_revenue; N/A when recognized_revenue == 0",
        "KPI layer (economics engine returns 0.0 on zero revenue; KPI overrides to N/A)",
        "single currency", "derived",
        "N/A when denominator is 0 (never 0.0, never fabricated)", ACTIVE),
    "roi": _c(
        "roi", "ROI",
        "Return on investment. DEFERRED — no engine implementation; awaits CEO activation.",
        "DEFERRED", "none",
        "n/a", "n/a", "not computed or displayed until authorized", DEFERRED),
    "cash": _c(
        "cash", "Cash Received",
        "DEFERRED — depends on WP-R02 Payout/Cash source.",
        "DEFERRED", "WP-R02 (not available)",
        "n/a", "n/a",
        "never inferred from revenue/commission/Network-Paid status", DEFERRED),
    "net_cash_flow": _c(
        "net_cash_flow", "Net Cash Flow",
        "DEFERRED — depends on WP-R02 Payout/Cash source.",
        "DEFERRED", "WP-R02 (not available)",
        "n/a", "n/a", "distinct from Net Profit; never equated", DEFERRED),
}


def get(kpi_id: str) -> Dict:
    if kpi_id not in KPI_CONTRACTS:
        raise KeyError(f"unknown KPI: {kpi_id}")
    return KPI_CONTRACTS[kpi_id]


def active_ids() -> list:
    return [k for k, v in KPI_CONTRACTS.items() if v["status"] == ACTIVE]


def deferred_ids() -> list:
    return [k for k, v in KPI_CONTRACTS.items() if v["status"] == DEFERRED]


# ---- drift guards: this module must not invent vocabulary (asserted at import) ----
# Revenue labels referenced here must be a subset of the canonical set in provenance.
_REFERENCED_LABELS = {"PRODUCTION_REVENUE", "UNVERIFIED_REVENUE", "SIMULATED_REVENUE"}
assert _REFERENCED_LABELS == provenance.REVENUE_LABELS, (
    "KPI contracts reference labels that differ from provenance.REVENUE_LABELS — no new enum allowed")
# Exactly the five canonical data states, no LIVE_UNVERIFIED / VERIFIED compound enum.
assert provenance.DATA_STATES == ["TEST", "DRY_RUN", "SEEDED", "LIVE", "PRODUCTION_VERIFIED"], (
    "canonical data_state vocabulary changed — WP-D05-01 must not alter it")
