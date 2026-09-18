"""AI Provider Router (PRD-009 C).

Providers: OpenAI, Vertex, Claude, Gemini. Key đọc từ env (không hardcode).
Routing policy + fallback + retry + timeout. DRY-RUN — không gọi API thật.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping

# provider → env key bắt buộc để coi là "available".
PROVIDERS: Dict[str, List[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "vertex": ["GCP_PROJECT", "VERTEX_MODEL"],
    "claude": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY"],
}


@dataclass
class RoutingPolicy:
    order: List[str] = field(default_factory=lambda: ["openai", "claude", "gemini", "vertex"])
    retries: int = 2
    timeout_s: int = 30


class AIRouter:
    def __init__(self, env: Mapping[str, str] | None = None, policy: RoutingPolicy | None = None):
        self.env = env or {}
        self.policy = policy or RoutingPolicy()

    def available(self, provider: str) -> bool:
        keys = PROVIDERS.get(provider, [])
        return bool(keys) and all(self.env.get(k) for k in keys)

    def select(self) -> str | None:
        """Chọn provider đầu tiên available theo order (routing policy)."""
        for p in self.policy.order:
            if self.available(p):
                return p
        return None

    def fallback_chain(self) -> List[str]:
        return [p for p in self.policy.order if self.available(p)]

    def route(self, prompt: str) -> Dict:
        """Trả kế hoạch định tuyến (dry-run). KHÔNG gọi API thật."""
        chain = self.fallback_chain()
        primary = chain[0] if chain else None
        return {
            "status": "dry-run",
            "primary": primary,
            "fallback": chain[1:],
            "retries": self.policy.retries,
            "timeout_s": self.policy.timeout_s,
            "ready": bool(primary),
            "note": "routing dry-run — chưa gọi API; gắn env key để bật provider",
        }
