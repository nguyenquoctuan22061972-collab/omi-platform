"""AWIN transaction -> durable conversion-chain mapping (S5B — additive, DRY-RUN).

Bridges the REUSED AWIN connector's transaction shape to RevenueStore.write_conversion_chain()
without modifying awin_live (no engine fork). Reuses awin_live.STATUS_MAP for status normalization.

The real AWIN transaction schema (verified in connectors/awin/awin_live.py:ingest_transactions):
  id, advertiserId, commissionStatus, saleAmount{amount,currency}, commissionAmount{amount,currency},
  clickDate, transactionDate.

No network, no credentials, no production call. source defaults to the TEST source; the live source
(awin_production) is only used once a production transport + CTO approval exist (deferred).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Mapping

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "connectors", "awin"))
from awin_live import STATUS_MAP  # noqa: E402  (reuse the connector's status mapping, no fork)


def _amount_currency(block) -> tuple:
    if isinstance(block, dict):
        return block.get("amount", 0), block.get("currency", "")
    return (block or 0), ""


def map_awin_transaction(txn: Mapping, source: str = "awin_fake_test") -> Dict:
    """Map one AWIN transaction dict to the `action` shape write_conversion_chain() expects.
    Tolerates missing optional fields (amounts default 0); requires an id."""
    tid = txn.get("id")
    if tid in (None, ""):
        raise ValueError("awin transaction missing 'id' (source_record_id)")
    order_value, cur_s = _amount_currency(txn.get("saleAmount"))
    comm_amount, cur_c = _amount_currency(txn.get("commissionAmount"))
    currency = cur_s or cur_c or "VND"
    status = STATUS_MAP.get(str(txn.get("commissionStatus", "")).lower(), "PENDING")
    return {
        "source": source,
        "source_record_id": str(tid),
        "tracking_link_id": "",
        "offer_id": "OF-" + str(txn.get("advertiserId", "")),
        "order_value": order_value,
        "commission_amount": comm_amount,
        "currency": currency,
        "status": status,
        "ts": txn.get("transactionDate", ""),
    }


def ingest_transactions_durable(store, txns: List[Mapping], *, source: str = "awin_fake_test",
                                data_state: str = "DRY_RUN", on_duplicate: str = "skip") -> Dict:
    """Map + write each AWIN transaction through the durable chain writer (one transaction each).
    Idempotent by default (duplicates skipped). Returns a summary. No production call."""
    written = skipped = errors = 0
    error_ids = []
    for t in txns:
        try:
            action = map_awin_transaction(t, source=source)
        except ValueError:
            errors += 1
            error_ids.append(t.get("id"))
            continue
        ok = store.write_conversion_chain(action, data_state=data_state, on_duplicate=on_duplicate)
        if ok:
            written += 1
        else:
            skipped += 1
    return {"written": written, "skipped": skipped, "errors": errors,
            "error_ids": error_ids, "source": source, "data_state": data_state}
