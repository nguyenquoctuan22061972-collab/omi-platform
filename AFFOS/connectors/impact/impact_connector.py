"""Impact seed/DRY-RUN connector — AFFOS.1. Offline seed catalog (no network).

Mirrors the generic/AWIN seed pattern. LIVE goes through impact_live.ImpactLiveClient.
Seed data is labeled SEEDED and can never be REAL.
"""
from __future__ import annotations

import os
import sys as _sys
from typing import Dict, Mapping, Optional

_sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
import provenance  # noqa: E402

SEED_CATALOG = [
    {"product_id": "IMP-1", "title": "Khoá học online Premium", "price": 1990000, "commission_rate": 0.30},
    {"product_id": "IMP-2", "title": "Phần mềm SaaS (gói năm)", "price": 3600000, "commission_rate": 0.20},
]


class ImpactConnector:
    name = "impact"
    required_env = ["IMPACT_ACCOUNT_SID", "IMPACT_AUTH_TOKEN"]

    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self.env = env or {}

    def is_live(self) -> bool:
        return all(self.env.get(k) for k in self.required_env)

    def fetch_offers(self) -> Dict:
        if self.is_live():
            return {"mode": "live_pending", "note": "cần IMPACT creds để gọi API thật (PR-005)", "offers": []}
        return {"mode": "dry-run", "offers": SEED_CATALOG}

    def ingest(self, repo, merchant_id: str = "IMP-M1") -> Dict:
        data = self.fetch_offers()
        n = 0
        for o in data["offers"]:
            repo.insert("products", {"id": o["product_id"], "merchant_id": merchant_id,
                                     "title": o["title"], "price": o["price"], "currency": "VND"})
            repo.insert("offers", {"id": "OF-" + o["product_id"], "product_id": o["product_id"],
                                   "merchant_id": merchant_id, "commission_rate": o["commission_rate"], "active": 1,
                                   **provenance.provenance("impact_seed", o["product_id"], "SEEDED")})
            n += 1
        return {"mode": data["mode"], "ingested": n}
