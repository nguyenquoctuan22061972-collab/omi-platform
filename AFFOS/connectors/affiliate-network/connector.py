"""AFFOS Affiliate-Network connector (PRD-017). ONE real connector.

Reuse pattern libs/integrations base (env-gated, dry-run). fetch_offers() trả dữ liệu:
- LIVE khi có AFFILIATE_API_KEY (chưa bật ở đây — cần credential, gọi mạng) → PR-005.
- DRY-RUN mặc định: trả seed catalog để chạy toàn chuỗi offline.
ingest(repo) ghi products + offers vào Data Access. Không network ở dry-run.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional

SEED_CATALOG = [
    {"product_id": "MP-1", "title": "Máy lọc nước Premium", "price": 4990000, "commission_rate": 0.10},
    {"product_id": "MP-2", "title": "Tai nghe không dây", "price": 890000, "commission_rate": 0.08},
]


class AffiliateNetworkConnector:
    name = "affiliate_network"
    required_env = ["AFFILIATE_API_KEY", "AFFILIATE_NETWORK_ID"]

    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self.env = env or {}

    def is_live(self) -> bool:
        return all(self.env.get(k) for k in self.required_env)

    def fetch_offers(self) -> Dict:
        if self.is_live():
            # LIVE path cần gọi API thật (credential) → chưa bật trong repo.
            return {"mode": "live_pending", "note": "cần AFFILIATE_API_KEY để gọi API thật (PR-005)",
                    "offers": []}
        return {"mode": "dry-run", "offers": SEED_CATALOG}

    def ingest(self, repo, merchant_id: str = "M-1") -> Dict:
        data = self.fetch_offers()
        n = 0
        for o in data["offers"]:
            repo.insert("products", {"id": o["product_id"], "merchant_id": merchant_id,
                                     "title": o["title"], "price": o["price"], "currency": "VND"})
            repo.insert("offers", {"id": "OF-" + o["product_id"], "product_id": o["product_id"],
                                   "merchant_id": merchant_id, "commission_rate": o["commission_rate"], "active": 1})
            n += 1
        return {"mode": data["mode"], "ingested": n}
