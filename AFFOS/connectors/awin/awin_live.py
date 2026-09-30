"""AWIN LIVE adapter (PRD-017 / CTO AWIN LIVE IMPLEMENTATION).

Real production HTTP transport + auth (env secrets only) + offer/transaction retrieval.
Economic-truth guards:
  - ProductionTransport calls api.awin.com over HTTPS (urllib). It NEVER returns seed data.
  - FakeTransport (tests) is fully isolated; is_production=False → records stamped TEST, never REAL.
  - Failures stay explicit (auth/permission/http/network/empty) and remain NON-REAL.
  - Production records: data_state=PRODUCTION_VERIFIED + is_verified ONLY from a production
    transport, with explicit currency (never assumed VND), persisted ONLY via a LIVE
    (Postgres) repository — SQLite is refused for production writes.
No secret is printed, logged, or returned.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Mapping, Optional
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
import provenance  # noqa: E402

AWIN_BASE = "https://api.awin.com"
AWIN_CREAD = "https://www.awin1.com/cread.php"

# Awin commissionStatus → normalized transaction_status (only APPROVED is realizable downstream).
STATUS_MAP = {
    "pending": "PENDING", "approved": "APPROVED", "confirmed": "APPROVED",
    "declined": "DECLINED", "rejected": "DECLINED",
    "cancelled": "CANCELLED", "canceled": "CANCELLED", "deleted": "CANCELLED",
    "refunded": "REFUNDED",
}
SQLITE_STATES = {"TEST", "DRY_RUN", "SEEDED"}


class AwinError(RuntimeError): pass
class AwinAuthError(AwinError): pass
class AwinPermissionError(AwinError): pass
class AwinHTTPError(AwinError): pass
class AwinNetworkError(AwinError): pass
class AwinCurrencyError(AwinError): pass
class ProductionStorageError(AwinError): pass


class Transport:
    is_production = False
    def get(self, url: str, token: str) -> Dict:  # pragma: no cover
        raise NotImplementedError


class ProductionTransport(Transport):
    """Real Awin Publisher API over HTTPS. Requires egress + token. NEVER returns seed."""
    is_production = True

    def get(self, url: str, token: str) -> Dict:
        import urllib.error
        import urllib.request
        if not token:
            raise AwinAuthError("missing token")
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode()
        except urllib.error.HTTPError as e:
            if e.code in (401,):
                raise AwinAuthError(f"auth failed HTTP {e.code}") from None
            if e.code in (403,):
                raise AwinPermissionError(f"permission denied HTTP {e.code}") from None
            raise AwinHTTPError(f"HTTP {e.code}") from None
        except urllib.error.URLError as e:
            raise AwinNetworkError(f"network error: {e.reason}") from None
        try:
            return json.loads(body)
        except Exception:
            raise AwinHTTPError("non-JSON production response") from None


class AwinLiveClient:
    def __init__(self, env: Optional[Mapping[str, str]] = None, transport: Optional[Transport] = None):
        self.env = dict(env or {})
        self.transport = transport
        self.token = self.env.get("AWIN_API_TOKEN", "")
        self.pid = self.env.get("AWIN_PUBLISHER_ID", "")

    # ---- 1. AUTH / 2. PUBLISHER VERIFY ----
    def auth(self) -> Dict:
        if not self.token:
            return {"step": "auth", "ok": False, "blocked": "AWIN_API_TOKEN (PR-005)"}
        if self.transport is None:
            return {"step": "auth", "ok": False, "blocked": "transport (egress/PR-002)"}
        return {"step": "auth", "ok": True}

    def publisher_verify(self) -> Dict:
        if not self.pid:
            return {"step": "publisher_verify", "ok": False, "blocked": "AWIN_PUBLISHER_ID (PR-005)"}
        return {"step": "publisher_verify", "ok": True, "publisher_id": self.pid}

    def _ready(self) -> bool:
        return bool(self.auth().get("ok") and self.publisher_verify().get("ok"))

    def _is_production(self) -> bool:
        return bool(self.transport and self.transport.is_production)

    def _state(self) -> str:
        return "PRODUCTION_VERIFIED" if (self._ready() and self._is_production()) else "TEST"

    def _source(self) -> str:
        return "awin_production" if self._state() == "PRODUCTION_VERIFIED" else "awin_fake_test"

    def _prov(self, rid: str, currency: str = "") -> Dict:
        st = self._state()
        if st == "PRODUCTION_VERIFIED" and not currency:
            raise AwinCurrencyError(f"production record {rid} thiếu currency (không mặc định VND)")
        cur = currency or "VND"   # VND fallback CHỈ cho TEST; production đã raise ở trên
        return provenance.provenance(self._source(), rid, st, currency=cur,
                                     is_verified=(st == "PRODUCTION_VERIFIED"))

    def _guard_repo_for_production(self, repo) -> None:
        if self._state() == "PRODUCTION_VERIFIED" and getattr(repo, "data_state", None) in SQLITE_STATES:
            raise ProductionStorageError("production data phải ghi vào Postgres (LIVE), không SQLite")

    # ---- 3. REAL OFFER ----
    def get_offers(self) -> Dict:
        if not self._ready():
            return {"step": "offers", "ok": False, "blocked": "auth/publisher"}
        data = self.transport.get(
            f"{AWIN_BASE}/publishers/{self.pid}/programmes/?relationship=joined", self.token)
        progs = data.get("programmes", data if isinstance(data, list) else [])
        offers = []
        for p in progs:
            cur = p.get("currencyCode", "")
            offers.append({"id": f"OF-{p.get('id')}", "product_id": str(p.get("id")),
                           "commission_rate": p.get("commissionRate", 0),
                           **self._prov(str(p.get("id")), currency=cur)})
        return {"step": "offers", "ok": True, "offers": offers, "count": len(offers)}

    # ---- 4. REAL DEEP LINK ----
    def deep_link(self, merchant_id: str, target_url: str, clickref: str) -> str:
        return (f"{AWIN_CREAD}?awinmid={merchant_id}&awinaffid={self.pid}"
                f"&clickref={quote(clickref)}&ued={quote(target_url, safe='')}")

    # ---- 6-8. REAL TRANSACTION → CONVERSION + COMMISSION ----
    def ingest_transactions(self, repo, start: str, end: str) -> Dict:
        if not self._ready():
            return {"step": "transactions", "ok": False, "blocked": "auth/publisher"}
        self._guard_repo_for_production(repo)
        url = (f"{AWIN_BASE}/publishers/{self.pid}/transactions/"
               f"?startDate={start}&endDate={end}&timezone=UTC")
        data = self.transport.get(url, self.token)
        txns = data.get("transactions", data if isinstance(data, list) else [])
        n = 0
        for t in txns:
            tid = str(t.get("id"))
            sale = t.get("saleAmount") or {}
            comm = t.get("commissionAmount") or {}
            currency = (sale.get("currency") if isinstance(sale, dict) else "") or \
                       (comm.get("currency") if isinstance(comm, dict) else "")
            order_value = sale.get("amount", 0) if isinstance(sale, dict) else (sale or 0)
            comm_amount = comm.get("amount", 0) if isinstance(comm, dict) else (comm or 0)
            status = STATUS_MAP.get(str(t.get("commissionStatus", "")).lower(), "PENDING")
            ce, cv = f"CE-{tid}", f"CV-{tid}"
            repo.insert("click_events", {"id": ce, "tracking_link_id": "", "ts": t.get("clickDate", ""),
                        "event_subtype": provenance.click_type(self._state(), network_reported=True),
                        **self._prov(ce, currency=currency)})
            repo.insert("conversion_events", {"id": cv, "click_event_id": ce,
                        "offer_id": "OF-" + str(t.get("advertiserId", "")),
                        "order_value": order_value, "status": status, "ts": t.get("transactionDate", ""),
                        "event_subtype": provenance.conversion_type(self._state()),
                        **self._prov(cv, currency=currency)})
            repo.insert("commissions", {"id": f"CO-{tid}", "conversion_event_id": cv,
                        "amount": comm_amount, "status": status,
                        **self._prov(f"CO-{tid}", currency=currency)})
            n += 1
        return {"step": "transactions", "ok": True, "ingested": n,
                "data_state": self._state(), "note": "empty production result stays non-real" if n == 0 else ""}

    def chain_status(self) -> Dict:
        steps = ["auth", "publisher_verify", "offers", "deep_link", "tracking",
                 "transactions", "commission", "revenue", "contribution_profit"]
        ready = self._ready() and self._is_production()
        return {"steps": steps, "ready_for_real": ready, "data_state": self._state(),
                "blocked_by": [] if ready else ["AWIN production credential", "transport/egress (PR-002)"]}
