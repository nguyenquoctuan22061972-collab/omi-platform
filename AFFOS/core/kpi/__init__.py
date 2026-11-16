"""AFFOS KPI Contract & Query Foundation (WP-D05-01).

READ-ONLY KPI layer that REUSES the existing engines — it never forks or mutates them:
  - money_status  : canonical confirmed/refund classification.
  - provenance    : data_state vocabulary, revenue_label, is_real (production-verified guard).
  - economics     : contribution_profit (Net Profit / cost breakdown).
  - attribution   : per-campaign aggregates (read-only).

Scope (CEO-approved D1–D6):
  - Recognized Revenue = Σ(confirmed − refund) restricted to provenance.is_real rows
    (PRODUCTION_VERIFIED + is_verified=1 + source∈PRODUCTION_SOURCES). No Impact-specific filter
    is added (D2 out of scope), so Impact production rows ARE counted if is_real.
  - Net Profit = Recognized Revenue − Total Costs (economics.contribution_profit).
  - Margin     = N/A when the revenue denominator is 0 (handled here, engine unchanged).
  - ROI / Cash / Net Cash Flow = DEFERRED (ROI pending; Cash depends on WP-R02).
  - Currency-aware: never aggregate across currencies without an approved FX policy.

This package adds NO new data_state/enum, NO schema, NO migration, and modifies NO existing file.
"""
from __future__ import annotations

__all__ = ["contracts", "query"]
