"""AFFOS Connector adapters (FAST-TRACK #03 Phase 2).

Wrap EXISTING connectors behind the generic Connector interface — reuse, no rewrite:
  - AffiliateNetworkAdapter  -> reuses connectors/affiliate-network (seed/dry-run)
  - AwinAdapter              -> reuses connectors/awin/awin_live.AwinLiveClient (LIVE)

The Revenue Pipeline is NOT modified; it keeps using AffiliateNetworkConnector directly.
These adapters only ADD the 8-capability surface. Nothing is labeled REAL here.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "core"))
sys.path.insert(0, os.path.join(_HERE, "affiliate-network"))
sys.path.insert(0, os.path.join(_HERE, "awin"))
sys.path.insert(0, os.path.join(_HERE, "impact"))

from connector_interface import Connector, envelope           # noqa: E402
from affiliate_network_connector import AffiliateNetworkConnector  # noqa: E402
import awin_live                                               # noqa: E402
from awin_live import AwinLiveClient, STATUS_MAP, AWIN_BASE    # noqa: E402
from impact_live import ImpactLiveClient, STATUS_MAP as IMPACT_STATUS_MAP, IMPACT_BASE  # noqa: E402


# ----------------------------------------------------------------------------
class AffiliateNetworkAdapter(Connector):
    """Generic seed/dry-run connector behind the interface. Serves SEED catalog."""

    name = "affiliate_network"

    def __init__(self, env: Optional[Dict] = None):
        self._c = AffiliateNetworkConnector(env or {})

    def mode(self) -> str:
        return "LIVE" if self._c.is_live() else "SEED"

    def _offers_raw(self):
        return self._c.fetch_offers().get("offers", [])

    def get_merchants(self) -> Dict:
        offs = self._offers_raw()
        merchants = [{"id": "M-1", "name": "Seed Merchant", "network": self.name}] if offs else []
        return envelope("get_merchants", self.mode(), merchants)

    def get_products(self) -> Dict:
        items = [{"id": o["product_id"], "title": o.get("title", ""),
                  "price": o.get("price", 0), "merchant_id": "M-1"} for o in self._offers_raw()]
        return envelope("get_products", self.mode(), items)

    def get_offers(self) -> Dict:
        items = [{"id": "OF-" + o["product_id"], "product_id": o["product_id"],
                  "commission_rate": o.get("commission_rate", 0)} for o in self._offers_raw()]
        return envelope("get_offers", self.mode(), items)

    def get_commission(self, offer_id: Optional[str] = None) -> Dict:
        items = [{"offer_id": "OF-" + o["product_id"], "commission_rate": o.get("commission_rate", 0)}
                 for o in self._offers_raw()]
        if offer_id:
            items = [i for i in items if i["offer_id"] == offer_id]
        return envelope("get_commission", self.mode(), items)

    def create_tracking_link(self, merchant_id: str, target_url: str, clickref: str) -> Dict:
        # Generic connector has no real network deep-link builder → synthetic SEED link.
        link = f"seed://track?m={merchant_id}&ref={clickref}&u={target_url}"
        return envelope("create_tracking_link", "SEED", [{"url": link, "note": "seed link, not a network deep link"}])

    def get_clicks(self, start: str = "", end: str = "") -> Dict:
        return envelope("get_clicks", self.mode(), [])      # seed connector reports no real clicks

    def get_conversions(self, start: str = "", end: str = "") -> Dict:
        return envelope("get_conversions", self.mode(), [])

    def get_revenue(self, start: str = "", end: str = "") -> Dict:
        return envelope("get_revenue", self.mode(), [])


# ----------------------------------------------------------------------------
class AwinAdapter(Connector):
    """AWIN behind the interface — reuses AwinLiveClient (auth/offers/deep_link/transactions).

    mode(): LIVE only when a production transport + creds are ready; otherwise DRY-RUN.
    Transaction reads are read-only (no repo write, no Postgres guard); they never
    fabricate and stay non-real unless the underlying transport is production.
    """

    name = "awin"

    def __init__(self, env: Optional[Dict] = None, transport=None):
        self.client = AwinLiveClient(env or {}, transport=transport)

    def mode(self) -> str:
        return "LIVE" if (self.client._ready() and self.client._is_production()) else "DRY-RUN"

    def _blocked(self, cap: str) -> Dict:
        return envelope(cap, self.mode(), [], ok=False, blocked="auth/publisher/transport")

    def get_offers(self) -> Dict:
        if not self.client._ready():
            return self._blocked("get_offers")
        r = self.client.get_offers()
        return envelope("get_offers", self.mode(), r.get("offers", []), ok=r.get("ok", False))

    def get_merchants(self) -> Dict:
        if not self.client._ready():
            return self._blocked("get_merchants")
        r = self.client.get_offers()   # AWIN programme == merchant/advertiser
        merchants = [{"id": "M-" + o.get("product_id", ""), "product_id": o.get("product_id", ""),
                      "network": self.name} for o in r.get("offers", [])]
        return envelope("get_merchants", self.mode(), merchants, ok=r.get("ok", False))

    def get_products(self) -> Dict:
        if not self.client._ready():
            return self._blocked("get_products")
        r = self.client.get_offers()
        items = [{"id": o.get("product_id", ""), "offer_id": o.get("id", ""),
                  "currency": o.get("currency", "")} for o in r.get("offers", [])]
        return envelope("get_products", self.mode(), items, ok=r.get("ok", False))

    def get_commission(self, offer_id: Optional[str] = None) -> Dict:
        if not self.client._ready():
            return self._blocked("get_commission")
        r = self.client.get_offers()
        items = [{"offer_id": o.get("id", ""), "commission_rate": o.get("commission_rate", 0),
                  "currency": o.get("currency", "")} for o in r.get("offers", [])]
        if offer_id:
            items = [i for i in items if i["offer_id"] == offer_id]
        return envelope("get_commission", self.mode(), items, ok=r.get("ok", False))

    def create_tracking_link(self, merchant_id: str, target_url: str, clickref: str) -> Dict:
        link = self.client.deep_link(merchant_id, target_url, clickref)  # real awin1 cread format
        return envelope("create_tracking_link", self.mode(), [{"url": link}])

    # ---- transaction-derived reads (read-only; reuse transport+token+STATUS_MAP) ----
    def _txns(self, start: str, end: str):
        cl = self.client
        url = (f"{AWIN_BASE}/publishers/{cl.pid}/transactions/"
               f"?startDate={start}&endDate={end}&timezone=UTC")
        data = cl.transport.get(url, cl.token)   # explicit failure propagates; never seed
        return data.get("transactions", data if isinstance(data, list) else [])

    def get_clicks(self, start: str = "", end: str = "") -> Dict:
        if not self.client._ready():
            return self._blocked("get_clicks")
        items = [{"id": "CE-" + str(t.get("id")), "ts": t.get("clickDate", "")}
                 for t in self._txns(start, end)]
        return envelope("get_clicks", self.mode(), items)

    def get_conversions(self, start: str = "", end: str = "") -> Dict:
        if not self.client._ready():
            return self._blocked("get_conversions")
        items = []
        for t in self._txns(start, end):
            sale = t.get("saleAmount") or {}
            items.append({"id": "CV-" + str(t.get("id")),
                          "order_value": sale.get("amount", 0) if isinstance(sale, dict) else sale,
                          "currency": sale.get("currency", "") if isinstance(sale, dict) else "",
                          "status": STATUS_MAP.get(str(t.get("commissionStatus", "")).lower(), "PENDING")})
        return envelope("get_conversions", self.mode(), items)

    def get_revenue(self, start: str = "", end: str = "") -> Dict:
        if not self.client._ready():
            return self._blocked("get_revenue")
        items = []
        for t in self._txns(start, end):
            comm = t.get("commissionAmount") or {}
            items.append({"id": "CO-" + str(t.get("id")),
                          "amount": comm.get("amount", 0) if isinstance(comm, dict) else comm,
                          "currency": comm.get("currency", "") if isinstance(comm, dict) else "",
                          "status": STATUS_MAP.get(str(t.get("commissionStatus", "")).lower(), "PENDING")})
        return envelope("get_revenue", self.mode(), items)


# ----------------------------------------------------------------------------
class ImpactAdapter(Connector):
    """Impact (impact.com) behind the interface — AFFOS.1. Reuses ImpactLiveClient.

    mode(): LIVE only when a production transport + creds are ready; otherwise DRY-RUN.
    Action reads are read-only (no repo write, no Postgres guard); never fabricate.
    NOTE: impact_production is not yet in PRODUCTION_SOURCES, so records are never is_real().
    """

    name = "impact"

    def __init__(self, env: Optional[Dict] = None, transport=None):
        self.client = ImpactLiveClient(env or {}, transport=transport)

    def mode(self) -> str:
        return "LIVE" if (self.client._ready() and self.client._is_production()) else "DRY-RUN"

    def _blocked(self, cap: str) -> Dict:
        return envelope(cap, self.mode(), [], ok=False, blocked="auth/publisher/transport")

    def get_offers(self) -> Dict:
        if not self.client._ready():
            return self._blocked("get_offers")
        r = self.client.get_offers()
        return envelope("get_offers", self.mode(), r.get("offers", []), ok=r.get("ok", False))

    def get_merchants(self) -> Dict:
        if not self.client._ready():
            return self._blocked("get_merchants")
        r = self.client.get_offers()
        merchants = [{"id": "M-" + o.get("product_id", ""), "product_id": o.get("product_id", ""),
                      "network": self.name} for o in r.get("offers", [])]
        return envelope("get_merchants", self.mode(), merchants, ok=r.get("ok", False))

    def get_products(self) -> Dict:
        if not self.client._ready():
            return self._blocked("get_products")
        r = self.client.get_offers()
        items = [{"id": o.get("product_id", ""), "offer_id": o.get("id", ""),
                  "currency": o.get("currency", "")} for o in r.get("offers", [])]
        return envelope("get_products", self.mode(), items, ok=r.get("ok", False))

    def get_commission(self, offer_id: Optional[str] = None) -> Dict:
        if not self.client._ready():
            return self._blocked("get_commission")
        r = self.client.get_offers()
        items = [{"offer_id": o.get("id", ""), "commission_rate": o.get("commission_rate", 0),
                  "currency": o.get("currency", "")} for o in r.get("offers", [])]
        if offer_id:
            items = [i for i in items if i["offer_id"] == offer_id]
        return envelope("get_commission", self.mode(), items, ok=r.get("ok", False))

    def create_tracking_link(self, merchant_id: str, target_url: str, clickref: str) -> Dict:
        link = self.client.deep_link(merchant_id, target_url, clickref)
        return envelope("create_tracking_link", self.mode(), [{"url": link}])

    def _actions(self, start: str, end: str):
        cl = self.client
        url = f"{IMPACT_BASE}/Mediapartners/{cl.sid}/Actions?StartDate={start}&EndDate={end}"
        data = cl.transport.get(url, cl._auth_header())
        return data.get("Actions", data if isinstance(data, list) else [])

    def get_clicks(self, start: str = "", end: str = "") -> Dict:
        if not self.client._ready():
            return self._blocked("get_clicks")
        items = [{"id": "CE-" + str(a.get("Id")), "ts": a.get("ClickDate", "")}
                 for a in self._actions(start, end)]
        return envelope("get_clicks", self.mode(), items)

    def get_conversions(self, start: str = "", end: str = "") -> Dict:
        if not self.client._ready():
            return self._blocked("get_conversions")
        items = [{"id": "CV-" + str(a.get("Id")), "order_value": a.get("Amount", 0),
                  "currency": a.get("Currency", ""),
                  "status": IMPACT_STATUS_MAP.get(str(a.get("State", "")).lower(), "PENDING")}
                 for a in self._actions(start, end)]
        return envelope("get_conversions", self.mode(), items)

    def get_revenue(self, start: str = "", end: str = "") -> Dict:
        if not self.client._ready():
            return self._blocked("get_revenue")
        items = [{"id": "CO-" + str(a.get("Id")), "amount": a.get("Payout", 0),
                  "currency": a.get("Currency", ""),
                  "status": IMPACT_STATUS_MAP.get(str(a.get("State", "")).lower(), "PENDING")}
                 for a in self._actions(start, end)]
        return envelope("get_revenue", self.mode(), items)


# ----------------------------------------------------------------------------
_REGISTRY = {"affiliate_network": AffiliateNetworkAdapter, "awin": AwinAdapter, "impact": ImpactAdapter}


def get_connector(name: str, env: Optional[Dict] = None, transport=None) -> Connector:
    """Factory. AWIN is proof network #1; Impact (AFFOS.1) is registered DRY-RUN."""
    key = (name or "").lower()
    if key not in _REGISTRY:
        raise ValueError(f"connector chưa đăng ký: {name} (chỉ: {sorted(_REGISTRY)})")
    if key == "awin":
        return AwinAdapter(env, transport=transport)
    if key == "impact":
        return ImpactAdapter(env, transport=transport)
    return AffiliateNetworkAdapter(env)
