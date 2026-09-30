"""AFFOS Revenue Pipeline (PRD-017). Chạy trọn chuỗi:
connector → click → conversion → commission → attribution → economics → profit.

Dữ liệu: dry-run/seed (chứng minh wiring). LIVE cần connector credential + Supabase (P0/P1).
Reuse: data_access.Repo, connector, attribution, economics. Không network ở dry-run.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_CORE = os.path.dirname(__file__)
sys.path.insert(0, _CORE)
sys.path.insert(0, os.path.join(_CORE, "attribution"))
sys.path.insert(0, os.path.join(_CORE, "..", "connectors", "affiliate-network"))
from data_access import Repo            # noqa: E402
import provenance          # noqa: E402
import proof               # noqa: E402
import attribution                      # noqa: E402
from affiliate_network_connector import AffiliateNetworkConnector  # noqa: E402


def _ts():
    return datetime.now(timezone.utc).isoformat()


def run(events: Optional[List[Dict]] = None, env: Optional[Dict] = None,
        costs: Optional[Dict] = None, connector=None) -> Dict:
    """events: [{product_id, clicks:int, conversions:[order_value,...]}] — nguồn dữ liệu.
    Nếu None → seed demo. Trả attribution + profit + data_source."""
    env = env or {}
    costs = costs or {}
    repo = Repo()
    conn = connector if connector is not None else AffiliateNetworkConnector(env)
    ing = conn.ingest(repo)
    DS = 'SEEDED' if ing['mode'] == 'dry-run' else 'LIVE'
    src = getattr(conn, 'name', 'seed')

    if events is None and hasattr(conn, 'fetch_report'):
        rep = conn.fetch_report()
        if rep:
            events = rep
    events = events if events is not None else [
        {"product_id": "MP-1", "clicks": 50, "conversions": [4990000, 4990000]},
        {"product_id": "MP-2", "clicks": 30, "conversions": [890000]},
    ]
    for ev in events:
        pid = ev["product_id"]; offer = "OF-" + pid
        camp = "C-" + pid; link = "L-" + pid
        rate = repo.query("SELECT commission_rate FROM offers WHERE id=?", (offer,))
        rate = rate[0]["commission_rate"] if rate else 0.0
        repo.insert("campaigns", {"id": camp, "offer_id": offer, "name": "Camp " + pid, "status": "active"})
        repo.insert("tracking_links", {"id": link, "campaign_id": camp, "offer_id": offer,
                                       "slug": pid.lower(), "target_url": "https://x/" + pid})
        for i in range(ev.get("clicks", 0)):
            repo.insert("click_events", {"id": f"CE-{pid}-{i}", "tracking_link_id": link, "ts": _ts(),
                        "event_subtype": provenance.click_type(DS),
                        **provenance.provenance(src, f"CE-{pid}-{i}", DS)})
        for j, ov in enumerate(ev.get("conversions", [])):
            ce = f"CE-{pid}-{j}"   # gán conversion vào click j (attribution last-click)
            cv = f"CV-{pid}-{j}"
            repo.insert("conversion_events", {"id": cv, "click_event_id": ce, "offer_id": offer,
                                              "order_value": ov, "status": "confirmed", "ts": _ts(),
                                              "event_subtype": provenance.conversion_type(DS),
                                              **provenance.provenance(src, cv, DS)})
            repo.insert("commissions", {"id": f"CO-{pid}-{j}", "conversion_event_id": cv,
                                        "amount": round(ov * rate, 2), "status": "confirmed",
                                        **provenance.provenance(src, f"CO-{pid}-{j}", DS)})

    per = attribution.per_campaign(repo)
    tot = attribution.totals(repo, ai_cost=costs.get("ai_cost", 0),
                             content_cost=costs.get("content_cost", 0),
                             infrastructure_cost=costs.get("infrastructure_cost", 0),
                             advertising_cost=costs.get("advertising_cost", 0))
    return {"data_source": ing["mode"], "data_state": DS,
            "real_commerce_proof": proof.real_commerce_proof(repo),
            "connector_ingested": ing["ingested"],
            "per_campaign": per, "totals": tot,
            "counts": {t: repo.count(t) for t in ["products", "offers", "campaigns",
                                                  "click_events", "conversion_events", "commissions"]}}
