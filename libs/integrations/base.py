"""Adapter base interface (PRD-006 §2). Credential env-only, dry-run, không network."""
from __future__ import annotations

from typing import Dict, List, Mapping


class DryRunResult(dict):
    """Kết quả dry-run (không gọi API thật)."""


class Adapter:
    """Base adapter thống nhất cho mọi provider.

    Subclass đặt `name` và `required_env`. Không thực hiện I/O mạng.
    """

    name: str = "base"
    required_env: List[str] = []

    def __init__(self, env: Mapping[str, str] | None = None):
        env = env or {}
        # Chỉ đọc từ env; không nhận secret literal qua code.
        self.config: Dict[str, str] = {k: env.get(k, "") for k in self.required_env}

    def is_configured(self) -> bool:
        return all(self.config.get(k) for k in self.required_env)

    def health(self) -> Dict:
        return {
            "adapter": self.name,
            "configured": self.is_configured(),
            "missing_env": [k for k in self.required_env if not self.config.get(k)],
            "mode": "dry-run",
        }

    def send(self, payload: Dict) -> DryRunResult:
        """Dry-run: KHÔNG gọi API thật. Trả mô tả hành động sẽ thực hiện."""
        return DryRunResult(
            status="dry-run",
            adapter=self.name,
            configured=self.is_configured(),
            would_send=payload,
            note="Chưa gọi API thật — gắn credential + bật production để kích hoạt.",
        )
