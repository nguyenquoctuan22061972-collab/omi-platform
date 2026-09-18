"""Kiểu dữ liệu domain (PRD-001 §7)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# 6 giai đoạn pipeline hợp lệ theo PRD §7.
PIPELINE_STAGES: List[str] = [
    "lead",
    "contacted",
    "qualified",
    "proposal",
    "won",
    "lost",
]


@dataclass
class Contact:
    id: str
    name: str = ""
    phone: str = ""
    email: str = ""
    source: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""


@dataclass
class Conversation:
    id: str
    contact_id: str
    channel: str
    message: str
    timestamp: str
