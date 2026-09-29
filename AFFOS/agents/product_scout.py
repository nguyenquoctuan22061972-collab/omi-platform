"""Product Scout (AGENT-PRODUCT-001, PRD-017). Chấm điểm cơ hội & phát opportunity.created.

Tôn trọng permissions: CANNOT spend_money/publish_content. Reuse economics.opportunity_score,
events.make_event. Chi phí ước tính bị chặn bởi cost_limit. Không network.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "core", "economics"))
sys.path.insert(0, os.path.join(_HERE, "..", "core", "intelligence"))
sys.path.insert(0, _HERE)
import economics                         # noqa: E402
import events                           # noqa: E402
from agent_spec import can, validate_agent  # noqa: E402

SPEC = json.load(open(os.path.join(_HERE, "registry", "product_scout.json"), encoding="utf-8"))


class ProductScout:
    def __init__(self, spec: Dict = SPEC, est_cost_per_scan: float = 0.05):
        self.spec = spec
        self.est_cost_per_scan = est_cost_per_scan
        self.spent = 0.0

    def _guard(self, action: str) -> None:
        if not can(self.spec, action):
            raise PermissionError(f"Product Scout KHÔNG được phép: {action}")

    def scan(self, candidates: List[Dict], top_k: int = 3) -> Dict:
        """candidates: [{master_product_id, demand, trend, conversion, epc, commission,
        content_fit, competition, production_cost}]. Trả top cơ hội + events."""
        self._guard("read_market_data")
        self._guard("create_opportunities")
        scored, evts = [], []
        for c in candidates:
            if self.spent + self.est_cost_per_scan > self.spec["cost_limit"]:
                break   # tôn trọng cost_limit
            self.spent += self.est_cost_per_scan
            score = economics.opportunity_score(
                c["demand"], c["trend"], c["conversion"], c["epc"], c["commission"],
                c["content_fit"], c["competition"], c["production_cost"])
            scored.append({"master_product_id": c.get("master_product_id", ""), "score": score})
        scored.sort(key=lambda r: r["score"], reverse=True)
        top = scored[:top_k]
        for o in top:
            evts.append(events.make_event("opportunity.created",
                        {"score": o["score"]}, o["master_product_id"]))
        return {"agent": self.spec["id"], "scanned": len(scored), "top": top,
                "events": evts, "spent": round(self.spent, 4)}

    def try_spend(self) -> Dict:
        """Chứng minh guardrail: hành động cấm phải bị chặn."""
        try:
            self._guard("spend_money")
            return {"blocked": False}
        except PermissionError as e:
            return {"blocked": True, "reason": str(e)}
