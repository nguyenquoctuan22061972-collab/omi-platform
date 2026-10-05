"""AFFOS first commercial output (SPRINT 02 — DRY-RUN vertical slice, additive).

Shortest revenue path for ONE niche:
  product → offer → commission(metadata) → campaign → tracking link → commercial-output JSON.

DRY-RUN / SEEDED only this sprint:
  - Writes to the in-memory SQLite dry-run repo (never Postgres).
  - REFUSES to run against a LIVE repo (LIVE writes go through runtime.awin_ingest, gated).
  - Every financial/event record carries provenance; nothing is labeled REAL.
  - Commission is an ESTIMATE on a reference order value — NOT a real commission (no conversion).
No AWIN live call, no secret read/printed.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Mapping, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "core"))
sys.path.insert(0, os.path.join(_HERE, "..", "connectors"))
sys.path.insert(0, _HERE)
import provenance                      # noqa: E402
from data_access import Repo           # noqa: E402
from adapters import get_connector     # noqa: E402
import runtime                         # noqa: E402

DEFAULT_NICHE = "home-living"          # 1 vertical first (no general marketplace yet)


def build_output(env: Optional[Mapping[str, str]] = None, niche: str = DEFAULT_NICHE,
                 reference_order_value: float = 1_000_000) -> Dict:
    env = dict(env or {})
    mode = runtime.repository_mode(env)
    if mode == "LIVE":
        return {"status": "REFUSED", "data_state": "n/a",
                "reason": "commercial_output is DRY-RUN only this sprint; "
                          "LIVE writes go through runtime.awin_ingest (gated).",
                "real_commerce_proof": "NOT YET VERIFIED"}

    repo = Repo(data_state="DRY_RUN")                       # SQLite dry-run
    conn = get_connector("affiliate_network", env)         # SEED connector (no AWIN live)
    merchant_id = "M-" + niche

    products = conn.get_products()["items"]
    offers = conn.get_offers()["items"]
    if not products or not offers:
        return {"status": "NO_INVENTORY", "data_state": "SEEDED",
                "reason": "seed connector returned no products/offers",
                "real_commerce_proof": "NOT YET VERIFIED"}

    p = products[0]
    o = next((x for x in offers if x["product_id"] == p["id"]), offers[0])
    DS = "SEEDED"
    src = "affiliate_network_seed"

    # --- persist the vertical slice with provenance ---
    repo.insert("products", {"id": p["id"], "merchant_id": merchant_id,
                             "title": p["title"], "price": p["price"], "currency": "VND"})
    repo.insert("offers", {"id": o["id"], "product_id": o["product_id"], "merchant_id": merchant_id,
                           "commission_rate": o["commission_rate"], "active": 1,
                           **provenance.provenance(src, o["id"], DS)})
    camp = "C-" + p["id"]
    link = "L-" + p["id"]
    repo.insert("campaigns", {"id": camp, "offer_id": o["id"],
                              "name": f"{niche} launch", "status": "active"})
    tl = conn.create_tracking_link(merchant_id, "https://shop.example/" + p["id"], camp)["items"][0]["url"]
    repo.insert("tracking_links", {"id": link, "campaign_id": camp, "offer_id": o["id"],
                                   "slug": p["id"].lower(), "target_url": tl})

    # --- validate provenance (must be non-real in DRY-RUN) ---
    offer_row = repo.query("SELECT * FROM offers WHERE id=?", (o["id"],))[0]
    assert not provenance.is_real(offer_row), "DRY-RUN offer must never be REAL"

    rate = o["commission_rate"]
    expected_commission = round(reference_order_value * rate, 2)

    return {
        "niche": niche,
        "product": {"id": p["id"], "title": p["title"], "price": p["price"], "currency": "VND"},
        "offer": {"id": o["id"], "commission_rate": rate},
        "commission": {"rate": rate, "currency": "VND",
                       "expected_on_reference_order": expected_commission,
                       "reference_order_value": reference_order_value,
                       "note": "ESTIMATE — no real conversion yet"},
        "campaign": {"id": camp, "name": f"{niche} launch", "status": "active"},
        "tracking_link": tl,
        "monetization": {"model": "affiliate_cps", "network": "affiliate_network(seed)"},
        "data_state": DS,
        "source": src,
        "is_real": provenance.is_real(offer_row),
        "status": "DRY_RUN_OUTPUT",
        "real_commerce_proof": "NOT YET VERIFIED",
    }


if __name__ == "__main__":
    import json
    niche = sys.argv[sys.argv.index("--niche") + 1] if "--niche" in sys.argv else DEFAULT_NICHE
    print(json.dumps(build_output(os.environ, niche=niche), ensure_ascii=False, indent=2))
