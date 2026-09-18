"""OpenAI adapter (dry-run). Credential env: OPENAI_API_KEY, OPENAI_MODEL.

Điểm cắm cho tác vụ AI (vd auto-tag nâng cao). Không gọi API thật.
"""
from .base import Adapter


class OpenAiAdapter(Adapter):
    name = "openai"
    required_env = ["OPENAI_API_KEY", "OPENAI_MODEL"]
