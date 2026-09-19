"""Affiliate registry (PRD-010 B): network + tracking id + campaign + UTM + deep-link.

Tracking id đọc từ env (`<NET>_TRACKING_ID`); không hardcode. Không gọi API thật.
"""
from __future__ import annotations

from typing import Dict, List, Mapping
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

NETWORKS = ["accesstrade", "shopee", "amazon", "tiktok_shop", "custom_partner"]

_ENV_KEY = {n: f"{n.upper()}_TRACKING_ID" for n in NETWORKS}


def build_utm(url: str, source: str, medium: str = "affiliate", campaign: str = "") -> str:
    """Gắn UTM params vào URL (giữ query cũ)."""
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query))
    q.update({"utm_source": source, "utm_medium": medium})
    if campaign:
        q["utm_campaign"] = campaign
    return urlunparse(parts._replace(query=urlencode(q)))


def deep_link(network: str, target_url: str, tracking_id: str) -> Dict:
    """Trừu tượng deep-link (KHÔNG gọi API rút gọn thật). Trả cấu trúc để service dựng link."""
    return {
        "network": network,
        "target": target_url,
        "tracking_id": tracking_id or "",
        "ready": bool(tracking_id),
        "note": "deep-link abstraction — service thật dựng URL khi có tracking id",
    }


class AffiliateRegistry:
    def __init__(self, env: Mapping[str, str] | None = None):
        self.env = env or {}

    def networks(self) -> List[str]:
        return list(NETWORKS)

    def tracking_id(self, network: str) -> str:
        if network not in NETWORKS:
            raise KeyError(f"network không hợp lệ: {network}")
        return self.env.get(_ENV_KEY[network], "")

    def is_configured(self, network: str) -> bool:
        return bool(self.tracking_id(network))

    def campaign_link(self, network: str, target_url: str, campaign: str = "") -> Dict:
        tid = self.tracking_id(network)
        utm = build_utm(target_url, source=network, campaign=campaign)
        return {**deep_link(network, utm, tid), "campaign": campaign, "utm_url": utm}

    def status(self) -> List[Dict]:
        return [{"network": n, "configured": self.is_configured(n)} for n in NETWORKS]
