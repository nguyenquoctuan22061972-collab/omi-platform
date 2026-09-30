"""AWIN LIVE chain (PRD-017 / CTO review). Scaffold thực thi:
AUTH → PUBLISHER VERIFY → REAL OFFER → REAL DEEP LINK → REAL TRACKING → REAL TRANSACTION
→ REAL COMMISSION → REAL REVENUE → REAL CONTRIBUTION PROFIT.

Nguyên tắc kinh tế-thật (CTO): record chỉ PRODUCTION_VERIFIED + is_verified khi đến từ
ProductionTransport (gọi api.awin.com thật với credential thật). FakeTransport (test) KHÔNG
BAO GIỜ tạo REAL — record gắn data_state='TEST'. Không có credential → mỗi bước 'blocked'.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Mapping, Optional
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
import provenance  # noqa: E402

AWIN_BASE = "https://api.awin.com"
AWIN_CREAD = "https://www.awin1.com/cread.php"


class Transport:
    is_production = False
    def get(self, url: str, token: str) -> Dict:  # pragma: no cover
        raise NotImplementedError


class ProductionTransport(Transport):
    """Gọi API Awin thật qua HTTPS. is_production=True → record có thể là REAL.
    (Chạy thật cần egress + credential — PR-005/PR-002.)"""
    is_production = True

    def get(self, url: str, token: str) -> Dict:  # pragma: no cover - cần mạng thật
        import json
        import urllib.request
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())


class AwinLiveClient:
    def __init__(self, env: Optional[Mapping[str, str]] = None, transport: Optional[Transport] = None):
        self.env = dict(env or {})
        self.transport = transport      # None → chưa có transport (blocked)
        self.token = self.env.get("AWIN_API_TOKEN", "")
        self.pid = self.env.get("AWIN_PUBLISHER_ID", "")

    # ---- 1. AUTH ----
    def auth(self) -> Dict:
        if not self.token:
            return {"step": "auth", "ok": False, "blocked": "AWIN_API_TOKEN (PR-005)"}
        if self.transport is None:
            return {"step": "auth", "ok": False, "blocked": "transport (egress/PR-002)"}
        return {"step": "auth", "ok": True}

    # ---- 2. PUBLISHER VERIFY ----
    def publisher_verify(self) -> Dict:
        if not self.pid:
            return {"step": "publisher_verify", "ok": False, "blocked": "AWIN_PUBLISHER_ID (PR-005)"}
        return {"step": "publisher_verify", "ok": True, "publisher_id": self.pid}

    def _ready(self) -> bool:
        return self.auth().get("ok") and self.publisher_verify().get("ok")

    def _state(self) -> str:
        # REAL chỉ khi transport production + sẵn sàng; ngược lại TEST (không real).
        if self._ready() and self.transport and self.transport.is_production:
            return "PRODUCTION_VERIFIED"
        return "TEST"

    def _source(self) -> str:
        return "awin_production" if self._state() == "PRODUCTION_VERIFIED" else "awin_fake_test"

    def _prov(self, rid: str) -> Dict:
        st = self._state()
        return provenance.provenance(self._source(), rid, st, is_verified=(st == "PRODUCTION_VERIFIED"))

    # ---- 3. REAL OFFER ----
    def get_offers(self) -> Dict:
        if not self._ready():
            return {"step": "offers", "ok": False, "blocked": "auth/publisher"}
        data = self.transport.get(f"{AWIN_BASE}/publishers/{self.pid}/programmes/?relationship=joined", self.token)
        offers = [{"id": f"OF-{p['id']}", "product_id": str(p["id"]), "commission_rate": p.get("commissionRate", 0),
                   **self._prov(str(p["id"]))} for p in data.get("programmes", data if isinstance(data, list) else [])]
        return {"step": "offers", "ok": True, "offers": offers}

    # ---- 4. REAL DEEP LINK (pure, deterministic) ----
    def deep_link(self, merchant_id: str, target_url: str, clickref: str) -> str:
        return (f"{AWIN_CREAD}?awinmid={merchant_id}&awinaffid={self.pid}"
                f"&clickref={quote(clickref)}&ued={quote(target_url, safe='')}")

    # ---- 6-8. REAL TRANSACTION → CONVERSION + COMMISSION ----
    def ingest_transactions(self, repo, start: str, end: str) -> Dict:
        if not self._ready():
            return {"step": "transactions", "ok": False, "blocked": "auth/publisher"}
        url = f"{AWIN_BASE}/publishers/{self.pid}/transactions/?startDate={start}&endDate={end}&timezone=UTC"
        data = self.transport.get(url, self.token)
        txns = data.get("transactions", data if isinstance(data, list) else [])
        n = 0
        for t in txns:
            tid = str(t.get("id"))
            cv = f"CV-{tid}"; ce = f"CE-{tid}"
            repo.insert("click_events", {"id": ce, "tracking_link_id": "", "ts": t.get("clickDate", ""),
                        "event_subtype": provenance.click_type(self._state(), network_reported=True), **self._prov(ce)})
            repo.insert("conversion_events", {"id": cv, "click_event_id": ce, "offer_id": "OF-" + str(t.get("advertiserId", "")),
                        "order_value": t.get("saleAmount", {}).get("amount", 0) if isinstance(t.get("saleAmount"), dict) else t.get("saleAmount", 0),
                        "status": t.get("commissionStatus", "pending"), "ts": t.get("transactionDate", ""),
                        "event_subtype": provenance.conversion_type(self._state()), **self._prov(cv)})
            comm = t.get("commissionAmount", {}).get("amount", 0) if isinstance(t.get("commissionAmount"), dict) else t.get("commissionAmount", 0)
            repo.insert("commissions", {"id": f"CO-{tid}", "conversion_event_id": cv, "amount": comm,
                        "status": t.get("commissionStatus", "pending"), **self._prov(f"CO-{tid}")})
            n += 1
        return {"step": "transactions", "ok": True, "ingested": n, "data_state": self._state()}

    # ---- Trạng thái toàn chuỗi ----
    def chain_status(self) -> Dict:
        steps = ["auth", "publisher_verify", "offers", "deep_link", "tracking",
                 "transactions", "commission", "revenue", "contribution_profit"]
        ready = self._ready() and self.transport is not None and self.transport.is_production
        return {"steps": steps, "ready_for_real": ready, "data_state": self._state(),
                "blocked_by": [] if ready else ["AWIN production credential", "transport/egress (PR-002)"]}
