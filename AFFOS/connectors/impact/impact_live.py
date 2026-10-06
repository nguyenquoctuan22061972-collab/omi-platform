"""Impact (impact.com) adapter — AFFOS.1 (PRD-017 / provider boundary).

Isolated provider module. Mirrors the AWIN economic-truth design WITHOUT touching AWIN:
  - ProductionTransport calls https://api.impact.com over HTTPS (urllib), HTTP Basic auth
    (AccountSID:AuthToken from env). It NEVER returns seed data.
  - FakeTransport (tests) is fully isolated; is_production=False -> records stamped TEST.
  - Failures stay explicit (auth/permission/http/network/empty) and remain NON-REAL.
  - source = impact_production (LIVE) / impact_fake_test (test). NOTE: impact_production is
    intentionally NOT yet in provenance.PRODUCTION_SOURCES, so even a production-transport
    Impact record is is_real()==False until the CTO whitelists it. Nothing is labeled REAL.
No secret is printed, logged, or returned.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from typing import Dict, Mapping, Optional
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
import provenance  # noqa: E402

IMPACT_BASE = "https://api.impact.com"

# Impact action/commission state -> normalized transaction_status.
STATUS_MAP = {
    "pending": "PENDING", "approved": "APPROVED", "confirmed": "APPROVED",
    "reversed": "REFUNDED", "declined": "DECLINED", "rejected": "DECLINED",
    "cancelled": "CANCELLED", "canceled": "CANCELLED",
}
SQLITE_STATES = {"TEST", "DRY_RUN", "SEEDED"}


def iso8601(value: str) -> str:
    """Normalize a date/datetime string to ISO-8601 date-time (Impact Actions API contract).

    A bare date 'YYYY-MM-DD' → 'YYYY-MM-DDT00:00:00Z' (Impact rejects date-only → HTTP 400).
    A value already carrying a time component ('T') is passed through unchanged.
    """
    v = (value or "").strip()
    if not v or "T" in v:
        return v
    return v + "T00:00:00Z"


class ImpactError(RuntimeError): pass
class ImpactAuthError(ImpactError): pass
class ImpactPermissionError(ImpactError): pass
class ImpactHTTPError(ImpactError): pass
class ImpactNetworkError(ImpactError): pass
class ImpactCurrencyError(ImpactError): pass
class ProductionStorageError(ImpactError): pass


class Transport:
    is_production = False
    def get(self, url: str, auth_header: str) -> Dict:  # pragma: no cover
        raise NotImplementedError


class ProductionTransport(Transport):
    """Real Impact Partner API over HTTPS. Requires egress + creds. NEVER returns seed."""
    is_production = True

    def get(self, url: str, auth_header: str) -> Dict:
        import urllib.error
        import urllib.request
        if not auth_header:
            raise ImpactAuthError("missing credentials")
        req = urllib.request.Request(url, headers={
            "Authorization": auth_header, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode()
        except urllib.error.HTTPError as e:
            # Surface the API error body (safe: it describes the request, carries no credential)
            # so a 4xx like a bad ActionDate format is diagnosable instead of a bare "HTTP 400".
            detail = ""
            try:
                detail = e.read().decode(errors="replace")[:300].replace("\n", " ").strip()
            except Exception:
                pass
            suffix = f": {detail}" if detail else ""
            if e.code == 401:
                raise ImpactAuthError(f"auth failed HTTP {e.code}{suffix}") from None
            if e.code == 403:
                raise ImpactPermissionError(f"permission denied HTTP {e.code}{suffix}") from None
            raise ImpactHTTPError(f"HTTP {e.code}{suffix}") from None
        except urllib.error.URLError as e:
            raise ImpactNetworkError(f"network error: {e.reason}") from None
        try:
            return json.loads(body)
        except Exception:
            raise ImpactHTTPError("non-JSON production response") from None


class ImpactLiveClient:
    def __init__(self, env: Optional[Mapping[str, str]] = None, transport: Optional[Transport] = None):
        self.env = dict(env or {})
        self.transport = transport
        self.sid = self.env.get("IMPACT_ACCOUNT_SID", "")
        self.token = self.env.get("IMPACT_AUTH_TOKEN", "")

    # ---- auth / verify ----
    def _auth_header(self) -> str:
        if not (self.sid and self.token):
            return ""
        raw = f"{self.sid}:{self.token}".encode()
        return "Basic " + base64.b64encode(raw).decode()

    def auth(self) -> Dict:
        if not self.token or not self.sid:
            return {"step": "auth", "ok": False, "blocked": "IMPACT_ACCOUNT_SID/IMPACT_AUTH_TOKEN (PR-005)"}
        if self.transport is None:
            return {"step": "auth", "ok": False, "blocked": "transport (egress/PR-002)"}
        return {"step": "auth", "ok": True}

    def publisher_verify(self) -> Dict:
        if not self.sid:
            return {"step": "publisher_verify", "ok": False, "blocked": "IMPACT_ACCOUNT_SID (PR-005)"}
        return {"step": "publisher_verify", "ok": True, "account_sid": self.sid}

    def _ready(self) -> bool:
        return bool(self.auth().get("ok") and self.publisher_verify().get("ok"))

    def _is_production(self) -> bool:
        return bool(self.transport and self.transport.is_production)

    def _state(self) -> str:
        return "PRODUCTION_VERIFIED" if (self._ready() and self._is_production()) else "TEST"

    def _source(self) -> str:
        return "impact_production" if self._state() == "PRODUCTION_VERIFIED" else "impact_fake_test"

    def _prov(self, rid: str, currency: str = "") -> Dict:
        st = self._state()
        if st == "PRODUCTION_VERIFIED" and not currency:
            raise ImpactCurrencyError(f"production record {rid} thiếu currency (không mặc định VND)")
        cur = currency or "VND"   # VND fallback CHỈ cho TEST
        # is_verified stays effectively non-real downstream: impact_production is NOT yet in
        # provenance.PRODUCTION_SOURCES, so is_real() returns False regardless.
        return provenance.provenance(self._source(), rid, st, currency=cur,
                                     is_verified=(st == "PRODUCTION_VERIFIED"))

    def _guard_repo_for_production(self, repo) -> None:
        if self._state() == "PRODUCTION_VERIFIED" and getattr(repo, "data_state", None) in SQLITE_STATES:
            raise ProductionStorageError("production data phải ghi vào Postgres (LIVE), không SQLite")

    # ---- offer discovery: Catalogs → Catalog Items ----
    def _catalogs(self) -> list:
        """Impact Publisher API: list the publisher's catalogs (one per advertiser/merchant)."""
        url = f"{IMPACT_BASE}/Mediapartners/{self.sid}/Catalogs?Page=1&PageSize=100"
        data = self.transport.get(url, self._auth_header())
        return data.get("Catalogs", data if isinstance(data, list) else [])

    def _catalog_items(self, catalog_id: str) -> list:
        """Impact Publisher API: items live UNDER a catalog, not at /Catalogs/Items."""
        url = (f"{IMPACT_BASE}/Mediapartners/{self.sid}/Catalogs/{quote(str(catalog_id))}/Items"
               f"?Page=1&PageSize=100")
        data = self.transport.get(url, self._auth_header())
        return data.get("Items", data if isinstance(data, list) else [])

    def get_offers(self) -> Dict:
        if not self._ready():
            return {"step": "offers", "ok": False, "blocked": "auth/publisher"}
        offers = []
        for c in self._catalogs():
            cid = str(c.get("Id", c.get("CatalogId", "")))
            adv = str(c.get("AdvertiserId", ""))
            merchant_id = ("M-" + adv) if adv else ""
            merchant_name = c.get("AdvertiserName", c.get("Name", ""))
            for it in self._catalog_items(cid):
                cur = it.get("Currency", "")
                pid = str(it.get("CatalogItemId", it.get("Id", "")))
                offers.append({"id": "OF-" + pid, "product_id": pid,
                               "catalog_id": cid, "merchant_id": merchant_id,
                               "merchant_name": merchant_name,
                               "title": it.get("Name", it.get("Title", "")),
                               "price": it.get("CurrentPrice", it.get("Price", 0)),
                               "commission_rate": it.get("PayoutRate", it.get("Payout", 0)),
                               **self._prov(pid, currency=cur)})
        return {"step": "offers", "ok": True, "offers": offers, "count": len(offers)}

    # ---- tracking link ----
    def deep_link(self, campaign_id: str, target_url: str, subid: str) -> str:
        return (f"{IMPACT_BASE}/Mediapartners/{self.sid}/TrackingLinks"
                f"?CampaignId={quote(campaign_id)}&SubId1={quote(subid)}&DeepLink={quote(target_url, safe='')}")

    # ---- actions -> conversion + commission ----
    def ingest_actions(self, repo, start: str, end: str) -> Dict:
        if not self._ready():
            return {"step": "actions", "ok": False, "blocked": "auth/publisher"}
        self._guard_repo_for_production(repo)
        # Impact Actions API filters by ActionDateStart/ActionDateEnd as ISO-8601 DATE-TIME
        # (date-only values are rejected with HTTP 400); pagination uses Page + PageSize.
        url = (f"{IMPACT_BASE}/Mediapartners/{self.sid}/Actions"
               f"?ActionDateStart={quote(iso8601(start))}&ActionDateEnd={quote(iso8601(end))}"
               f"&Page=1&PageSize=100")
        data = self.transport.get(url, self._auth_header())
        actions = data.get("Actions", data if isinstance(data, list) else [])
        n = 0
        for a in actions:
            aid = str(a.get("Id"))
            currency = a.get("Currency", "")
            amount = a.get("Amount", 0)
            payout = a.get("Payout", 0)
            status = STATUS_MAP.get(str(a.get("State", "")).lower(), "PENDING")
            ce, cv = f"CE-{aid}", f"CV-{aid}"
            repo.insert("click_events", {"id": ce, "tracking_link_id": "", "ts": a.get("ClickDate", ""),
                        "event_subtype": provenance.click_type(self._state(), network_reported=True),
                        **self._prov(ce, currency=currency)})
            repo.insert("conversion_events", {"id": cv, "click_event_id": ce,
                        "offer_id": "OF-" + str(a.get("CampaignId", "")),
                        "order_value": amount, "status": status, "ts": a.get("EventDate", ""),
                        "event_subtype": provenance.conversion_type(self._state()),
                        **self._prov(cv, currency=currency)})
            repo.insert("commissions", {"id": f"CO-{aid}", "conversion_event_id": cv,
                        "amount": payout, "status": status,
                        **self._prov(f"CO-{aid}", currency=currency)})
            n += 1
        return {"step": "actions", "ok": True, "ingested": n,
                "data_state": self._state(), "note": "empty production result stays non-real" if n == 0 else ""}

    def chain_status(self) -> Dict:
        steps = ["auth", "publisher_verify", "offers", "tracking_link", "click",
                 "action", "commission", "revenue", "contribution_profit"]
        ready = self._ready() and self._is_production()
        return {"steps": steps, "ready_for_real": ready, "data_state": self._state(),
                "provider": "impact",
                "blocked_by": [] if ready else ["Impact production credentials", "transport/egress (PR-002)",
                                                "impact_production not yet in PRODUCTION_SOURCES"]}
