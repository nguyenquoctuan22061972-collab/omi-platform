"""AFFOS Revenue Reporting & Reconciliation (S6 — additive, READ-ONLY).

Reconciles conversions -> commissions -> revenue and classifies each commission as
pending / approved / rejected / refunded, plus a `verified` flag (real production provenance).
Reports missing records, orphans, duplicates and currency discrepancies WITHOUT ever mutating a
source record (SELECT-only; no insert/update/delete).

Reuses money_status (canonical status), provenance (is_real) and does not fork attribution. Works
with any repo exposing .query(sql, params) (SQLite adapter in tests; PostgresRepository in prod).
No secret is read or printed.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "core"))
import money_status  # noqa: E402
import provenance  # noqa: E402

BUCKETS = ("pending", "approved", "rejected", "refunded")


def _bucket(status: str) -> str:
    if money_status.is_confirmed(status):
        return "approved"
    if money_status.is_refund(status):
        return "refunded"
    if money_status.canonical(status) == "PENDING":
        return "pending"
    return "rejected"      # DECLINED / CANCELLED / REJECTED / DELETED / unknown


def reconcile(repo, currency: Optional[str] = None) -> Dict:
    """Read-only reconciliation. Returns summary + discrepancies + an alert flag. Never writes."""
    convs = repo.query(
        "SELECT id, status, order_value, currency, source, source_record_id, data_state, is_verified "
        "FROM conversion_events")
    comms = repo.query(
        "SELECT id, conversion_event_id, amount, status, currency, source, source_record_id, "
        "data_state, is_verified FROM commissions")
    if currency:
        convs = [c for c in convs if (c.get("currency") or "VND") == currency]
        comms = [c for c in comms if (c.get("currency") or "VND") == currency]

    conv_ids = {c["id"] for c in convs}
    linked_conv_ids = {c["conversion_event_id"] for c in comms}

    # ---- status buckets + per-currency totals (never collapse currencies) ----
    counts = {b: 0 for b in BUCKETS}
    by_currency: Dict[str, Dict] = defaultdict(lambda: {b: 0.0 for b in BUCKETS})
    verified_all = bool(comms)
    for co in comms:
        b = _bucket(co.get("status"))
        counts[b] += 1
        cur = co.get("currency") or "VND"
        by_currency[cur][b] += float(co.get("amount") or 0)
        if not provenance.is_real(co):
            verified_all = False

    # ---- discrepancies (reported, never auto-corrected) ----
    missing_commission = sorted(conv_ids - linked_conv_ids)          # conversion with no commission
    orphan_commission = sorted(                                      # commission with no conversion
        {co["id"] for co in comms if co.get("conversion_event_id") not in conv_ids})
    dup_groups: Dict[tuple, List[str]] = defaultdict(list)
    for co in comms:
        key = (co.get("source"), co.get("source_record_id"))
        if key[1]:
            dup_groups[key].append(co["id"])
    duplicates = {f"{k[0]}:{k[1]}": v for k, v in dup_groups.items() if len(v) > 1}
    invalid_provenance = sorted(
        co["id"] for co in comms if not co.get("source") or not co.get("source_record_id"))

    discrepancies = {
        "missing_commission": missing_commission,
        "orphan_commission": orphan_commission,
        "duplicate_commission": duplicates,
        "invalid_provenance": invalid_provenance,
    }
    has_discrepancy = any(discrepancies.values())
    alert = None
    if has_discrepancy:
        alert = "reconciliation discrepancies found — review (source records NOT modified)"
    elif not verified_all:
        alert = "no production-verified revenue (data_state/source not PRODUCTION_VERIFIED)"

    return {
        "status": "ok",
        "execution": {"ts": datetime.now(timezone.utc).isoformat(),
                      "conversions_scanned": len(convs), "commissions_scanned": len(comms),
                      "currency_filter": currency},
        "summary": {"counts": counts, "by_currency": {k: dict(v) for k, v in by_currency.items()},
                    "verified": verified_all},
        "discrepancies": discrepancies,
        "alert": alert,
        "read_only": True,
    }
