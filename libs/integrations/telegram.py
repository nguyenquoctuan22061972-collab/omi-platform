"""Telegram adapter (dry-run). Credential env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID."""
from .base import Adapter


class TelegramAdapter(Adapter):
    name = "telegram"
    required_env = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
