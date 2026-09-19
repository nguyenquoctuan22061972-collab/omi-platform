"""Lead Engine (PRD-010 C): capture interface, email queue, Telegram notify (dry-run),
webhook abstraction, CRM mapping. Mock execution — không gọi API/gửi thật.

CRM mapping trả payload theo hợp đồng CRM Core PRD-001 §6 (không gọi API).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def crm_mapping(lead: Dict) -> Dict:
    """Map lead → payload POST /contacts (PRD-001). Không gọi API."""
    return {
        "name": lead.get("name", ""),
        "phone": lead.get("phone", ""),
        "email": lead.get("email", ""),
        "source": lead.get("source", "lead"),
        "tags": lead.get("tags", []),
    }


class EmailQueue:
    def __init__(self):
        self.queue: List[Dict] = []
        self.sent: List[Dict] = []

    def enqueue(self, to: str, subject: str, body: str) -> Dict:
        item = {"id": "eml_" + uuid.uuid4().hex[:12], "to": to, "subject": subject,
                "body": body, "ts": _now(), "status": "queued"}
        self.queue.append(item)
        return item

    def flush_dry_run(self) -> List[Dict]:
        """Dry-run: đánh dấu 'sent' nhưng KHÔNG gửi thật."""
        moved = []
        while self.queue:
            item = self.queue.pop(0)
            item["status"] = "sent-dry-run"
            self.sent.append(item)
            moved.append(item)
        return moved


class LeadEngine:
    def __init__(self):
        self.leads: List[Dict] = []
        self.email = EmailQueue()
        self.notifications: List[Dict] = []
        self.webhooks: List[Dict] = []

    def capture(self, name="", phone="", email="", source="form", tags=None) -> Dict:
        lead = {"id": "led_" + uuid.uuid4().hex[:12], "name": name, "phone": phone,
                "email": email, "source": source, "tags": tags or [], "ts": _now()}
        self.leads.append(lead)
        return lead

    def notify_telegram(self, lead: Dict) -> Dict:
        """Dry-run notify (dùng adapter thật khi có credential)."""
        note = {"channel": "telegram", "lead_id": lead["id"], "status": "dry-run", "ts": _now()}
        self.notifications.append(note)
        return note

    def register_webhook(self, url_env_key: str) -> Dict:
        """Trừu tượng webhook: chỉ lưu tên biến env (không URL/secret literal)."""
        wh = {"env_key": url_env_key, "status": "registered"}
        self.webhooks.append(wh)
        return wh

    def to_crm(self, lead: Dict) -> Dict:
        return crm_mapping(lead)
