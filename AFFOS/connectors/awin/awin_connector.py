"""AWIN connector (PRD-017). Real affiliate network = AWIN Publisher API.

Interface đồng nhất với affiliate-network connector (reuse pattern, no fork):
- is_live(): đủ AWIN_API_TOKEN + AWIN_PUBLISHER_ID.
- fetch_offers(): programmes/joined → products+offers. Dry-run seed nếu chưa có credential.
- fetch_report(): clicks + transactions (conversions) theo product → shape pipeline.
- ingest(repo): ghi products/offers.
Endpoint AWIN (không phải secret; token qua env, KHÔNG hardcode):
  base https://api.awin.com
  transactions: /publishers/{pid}/transactions/?startDate=..&endDate=..
  reports (aggregated): /publishers/{pid}/reports/aggregated/...
Live path cần gọi mạng + Bearer token → PR-005 (chưa bật trong repo).
"""
from __future__ import annotations

import os
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
import provenance  # noqa: E402

from typing import Dict, List, Mapping, Optional

BASE = "https://api.awin.com"
SEED_OFFERS = [
    {"product_id": "AWIN-PROG-1", "title": "AWIN Merchant A — Electronics", "price": 0, "commission_rate": 0.07},
    {"product_id": "AWIN-PROG-2", "title": "AWIN Merchant B — Home", "price": 0, "commission_rate": 0.05},
]
# transaction seed: order_value (commissionAmount tính từ rate) — mô phỏng AWIN transactions.
SEED_REPORT = [
    {"product_id": "AWIN-PROG-1", "clicks": 120, "conversions": [1500000, 2300000]},
    {"product_id": "AWIN-PROG-2", "clicks": 80, "conversions": [640000]},
]


class AwinConnector:
    name = "awin"
    required_env = ["AWIN_API_TOKEN", "AWIN_PUBLISHER_ID"]

    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self.env = env or {}

    def is_live(self) -> bool:
        return all(self.env.get(k) for k in self.required_env)

    def endpoints(self) -> Dict[str, str]:
        pid = self.env.get("AWIN_PUBLISHER_ID", "<publisherId>")
        return {"base": BASE,
                "transactions": f"{BASE}/publishers/{pid}/transactions/",
                "reports": f"{BASE}/publishers/{pid}/reports/aggregated/publisher"}

    def fetch_offers(self) -> Dict:
        if self.is_live():
            return {"mode": "live_pending", "note": "cần AWIN_API_TOKEN gọi API thật (PR-005)", "offers": []}
        return {"mode": "dry-run", "offers": SEED_OFFERS}

    def fetch_report(self) -> List[Dict]:
        if self.is_live():
            return []   # live: parse AWIN transactions → shape này (chưa bật, cần token)
        return SEED_REPORT

    def ingest(self, repo, merchant_id: str = "AWIN-M") -> Dict:
        data = self.fetch_offers()
        n = 0
        for o in data["offers"]:
            repo.insert("products", {"id": o["product_id"], "merchant_id": merchant_id,
                                     "title": o["title"], "price": o["price"], "currency": "VND"})
            repo.insert("offers", {"id": "OF-" + o["product_id"], "product_id": o["product_id"],
                                   "merchant_id": merchant_id, "commission_rate": o["commission_rate"], "active": 1,
                                   **provenance.provenance("awin_seed", o["product_id"], "SEEDED")})
            n += 1
        return {"mode": data["mode"], "ingested": n}
