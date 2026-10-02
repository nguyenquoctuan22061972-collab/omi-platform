"""AFFOS Connector Interface (PRD-017 / FAST-TRACK #03 Phase 2).

ONE generic contract so any affiliate network plugs in without touching the Revenue
Pipeline or the 10 AffOS pillars. Existing connectors are REUSED behind adapters
(see adapters.py) — nothing here rewrites them.

Exactly 8 required capabilities:
    get_merchants, get_products, get_offers, get_commission,
    create_tracking_link, get_clicks, get_conversions, get_revenue

Data honesty (never mislabel):
    SEED     — static seed catalog (no network)
    DRY-RUN  — wiring proof, no live call
    LIVE     — real production transport + creds (call attempted/made)
    REAL     — reserved: asserted ONLY by proof.real_commerce_proof after verification,
               never self-declared by a connector.
Every method returns the same envelope: {"capability","mode","ok","items","blocked"}.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

# Allowed data-mode labels a connector may self-declare. "REAL" is intentionally
# NOT here — only the proof gate may conclude REAL.
MODES = ("SEED", "DRY-RUN", "LIVE")

CAPABILITIES = (
    "get_merchants", "get_products", "get_offers", "get_commission",
    "create_tracking_link", "get_clicks", "get_conversions", "get_revenue",
)


def envelope(capability: str, mode: str, items, ok: bool = True,
             blocked: str = "") -> Dict:
    if mode not in MODES:
        raise ValueError(f"mode không hợp lệ: {mode} (REAL chỉ do proof gate kết luận)")
    return {"capability": capability, "mode": mode, "ok": ok,
            "items": items if items is not None else [], "blocked": blocked}


class Connector(ABC):
    """Generic affiliate-network connector contract (8 capabilities)."""

    name: str = "connector"

    @abstractmethod
    def mode(self) -> str:
        """Current data mode: SEED | DRY-RUN | LIVE (never REAL)."""

    @abstractmethod
    def get_merchants(self) -> Dict: ...

    @abstractmethod
    def get_products(self) -> Dict: ...

    @abstractmethod
    def get_offers(self) -> Dict: ...

    @abstractmethod
    def get_commission(self, offer_id: Optional[str] = None) -> Dict: ...

    @abstractmethod
    def create_tracking_link(self, merchant_id: str, target_url: str,
                             clickref: str) -> Dict: ...

    @abstractmethod
    def get_clicks(self, start: str = "", end: str = "") -> Dict: ...

    @abstractmethod
    def get_conversions(self, start: str = "", end: str = "") -> Dict: ...

    @abstractmethod
    def get_revenue(self, start: str = "", end: str = "") -> Dict: ...


def verify_contract(conn: Connector) -> Dict:
    """Static contract check: all 8 capabilities present + callable, mode valid."""
    missing = [c for c in CAPABILITIES if not callable(getattr(conn, c, None))]
    m = conn.mode()
    return {"name": getattr(conn, "name", "?"), "mode": m,
            "mode_valid": m in MODES, "missing_capabilities": missing,
            "contract_ok": (not missing) and (m in MODES)}
