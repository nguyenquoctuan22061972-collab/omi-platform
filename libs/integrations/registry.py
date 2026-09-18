"""Registry — tra adapter theo tên (PRD-006 §2)."""
from __future__ import annotations

from typing import Dict, List, Mapping, Type

from .base import Adapter
from .telegram import TelegramAdapter
from .gmail_smtp import GmailSmtpAdapter
from .zalo_oa import ZaloOaAdapter
from .facebook_messenger import FacebookMessengerAdapter
from .openai import OpenAiAdapter
from .vertex_ai import VertexAiAdapter

ADAPTERS: Dict[str, Type[Adapter]] = {
    cls.name: cls
    for cls in (
        TelegramAdapter,
        GmailSmtpAdapter,
        ZaloOaAdapter,
        FacebookMessengerAdapter,
        OpenAiAdapter,
        VertexAiAdapter,
    )
}


def get_adapter(name: str, env: Mapping[str, str] | None = None) -> Adapter:
    if name not in ADAPTERS:
        raise KeyError(f"adapter không tồn tại: {name}. Có: {list(ADAPTERS)}")
    return ADAPTERS[name](env or {})


def list_adapters() -> List[str]:
    return sorted(ADAPTERS)
