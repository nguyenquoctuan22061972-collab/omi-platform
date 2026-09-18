"""Gmail SMTP adapter (dry-run). Credential env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS."""
from .base import Adapter


class GmailSmtpAdapter(Adapter):
    name = "gmail_smtp"
    required_env = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]
