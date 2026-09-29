"""AFFOS Domain Events (PRD-017). Catalog + factory. master_product_id xuyên suốt."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

EVENTS = {
    "product.detected", "offer.updated", "price.changed",
    "content.created", "content.published", "link.clicked",
    "conversion.received", "commission.updated", "refund.detected",
    "opportunity.created", "agent.failed",
}


def make_event(name: str, payload: Optional[Dict] = None,
               master_product_id: str = "") -> Dict:
    if name not in EVENTS:
        raise ValueError(f"event không hợp lệ: {name}")
    return {"id": "evt_" + uuid.uuid4().hex[:16], "name": name,
            "ts": datetime.now(timezone.utc).isoformat(),
            "master_product_id": master_product_id, "payload": payload or {}}
