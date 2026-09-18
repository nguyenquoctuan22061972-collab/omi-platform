"""Module ingestion (PRD-001 §4 kênh đầu vào, §9.1-9.3).

Chuẩn hoá payload từ 6 kênh → contact (merge) + message (đúng contact) + auto-tag.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import contacts as _contacts
from . import conversations as _conversations
from . import tagging as _tagging


# 6 kênh hợp lệ theo PRD §4.
CHANNELS = {
    "facebook_messenger",
    "zalo_oa",
    "telegram",
    "email",
    "form_landing_page",
    "api_webhook",
}


def normalize_channel(raw: str) -> str:
    """Đưa tên kênh về dạng chuẩn snake_case; giữ nguyên nếu không nhận diện."""
    key = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "facebook": "facebook_messenger",
        "messenger": "facebook_messenger",
        "fb": "facebook_messenger",
        "zalo": "zalo_oa",
        "form": "form_landing_page",
        "landing": "form_landing_page",
        "webhook": "api_webhook",
        "api": "api_webhook",
    }
    return aliases.get(key, key)


def ingest(
    conn: sqlite3.Connection,
    channel: str,
    message: str = "",
    name: str = "",
    phone: str = "",
    email: str = "",
) -> dict:
    """Nhận lead/message từ 1 kênh: merge contact, auto-tag, ghi hội thoại.

    Trả về {contact, conversation}. Là bước "Lead vào từ nhiều kênh" (§9.1).
    """
    ch = normalize_channel(channel)
    tags = _tagging.suggest_tags(message=message, channel=ch)

    contact = _contacts.create_contact(
        conn, name=name, phone=phone, email=email, source=ch, tags=tags
    )

    conversation: Optional[dict] = None
    if message:
        conversation = _conversations.add_message(
            conn, channel=ch, message=message, contact_id=contact["id"]
        )

    return {"contact": _contacts.get_contact(conn, contact["id"]), "conversation": conversation}
