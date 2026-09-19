"""Alert Engine (PRD-012 E). Telegram + SMTP alert; chỉ gửi khi *_ENABLED=true; dry-run."""
from .engine import AlertEngine, ALERT_CHANNELS

__all__ = ["AlertEngine", "ALERT_CHANNELS"]
