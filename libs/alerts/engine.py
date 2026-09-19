"""Alert Engine (PRD-012 E). Telegram + SMTP; chỉ 'gửi' khi <CH>_ALERT_ENABLED=true.

DRY-RUN — không gọi API/gửi email thật. Credential từ env; không hardcode.
"""
from __future__ import annotations

from typing import Dict, List, Mapping

# channel → (enable flag, env cần)
ALERT_CHANNELS = {
    "telegram": ("TELEGRAM_ALERT_ENABLED", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]),
    "smtp": ("SMTP_ALERT_ENABLED", ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "ALERT_TO_EMAIL"]),
}


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


class AlertEngine:
    def __init__(self, env: Mapping[str, str] | None = None):
        self.env = env or {}

    def enabled(self, channel: str) -> bool:
        flag = ALERT_CHANNELS.get(channel, (None, []))[0]
        return bool(flag) and _truthy(self.env.get(flag, ""))

    def configured(self, channel: str) -> bool:
        keys = ALERT_CHANNELS.get(channel, (None, []))[1]
        return bool(keys) and all(self.env.get(k) for k in keys)

    def send(self, channel: str, severity: str, message: str) -> Dict:
        """Chỉ 'gửi' (dry-run) khi enabled + configured; ngược lại skipped. Không raise."""
        if channel not in ALERT_CHANNELS:
            return {"status": "error", "reason": "unknown_channel", "channel": channel}
        if not self.enabled(channel):
            return {"status": "skipped", "reason": "disabled", "channel": channel}
        if not self.configured(channel):
            return {"status": "skipped", "reason": "missing_env", "channel": channel}
        # Enabled + configured → vẫn dry-run ở phase này (chưa gọi API/SMTP thật).
        return {"status": "dry-run", "channel": channel, "severity": severity,
                "message": message[:500], "note": "chưa gửi thật — hiện thực API khi go-live"}

    def broadcast(self, severity: str, message: str) -> List[Dict]:
        return [self.send(ch, severity, message) for ch in ALERT_CHANNELS]
