"""Adapter activation layer (PRD-007 B). ADDITIVE — không đổi interface adapter.

Bổ sung: env validation, connection test (dry-run), enable flag, fail-safe fallback.
KHÔNG gọi API thật. Adapter mặc định TẮT tới khi <PREFIX>_ENABLED=true và đủ env.
"""
from __future__ import annotations

from typing import Dict, List, Mapping

from .base import Adapter
from .registry import ADAPTERS, get_adapter

# enable flag env theo adapter (prefix có thể khác tên adapter).
ENABLE_FLAG = {
    "telegram": "TELEGRAM_ENABLED",
    "gmail_smtp": "SMTP_ENABLED",
    "zalo_oa": "ZALO_OA_ENABLED",
    "facebook_messenger": "FB_PAGE_ENABLED",
    "openai": "OPENAI_ENABLED",
    "vertex_ai": "VERTEX_ENABLED",
}


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def is_enabled(name: str, env: Mapping[str, str]) -> bool:
    return _truthy(env.get(ENABLE_FLAG.get(name, ""), ""))


def validate_env(adapter: Adapter) -> Dict:
    """Kiểm tra đủ env chưa (không in giá trị)."""
    return {
        "adapter": adapter.name,
        "configured": adapter.is_configured(),
        "missing_env": [k for k in adapter.required_env if not adapter.config.get(k)],
    }


def connection_test(adapter: Adapter, env: Mapping[str, str]) -> Dict:
    """Dry-run connection test — KHÔNG mở kết nối/không gọi API."""
    enabled = is_enabled(adapter.name, env)
    configured = adapter.is_configured()
    return {
        "adapter": adapter.name,
        "enabled": enabled,
        "configured": configured,
        "mode": "dry-run",
        "ok": bool(enabled and configured),
        "note": "connection test dry-run — không gọi API thật",
    }


def safe_send(adapter: Adapter, payload: Dict, env: Mapping[str, str]) -> Dict:
    """Fail-safe: chỉ 'send' khi enabled+configured; ngược lại fallback, không raise."""
    if not is_enabled(adapter.name, env):
        return {"status": "skipped", "reason": "disabled", "adapter": adapter.name}
    if not adapter.is_configured():
        return {"status": "skipped", "reason": "missing_env", "adapter": adapter.name,
                "missing_env": [k for k in adapter.required_env if not adapter.config.get(k)]}
    # Enabled + configured: vẫn dry-run ở phase này (chưa gọi API thật).
    return adapter.send(payload)


def activation_report(env: Mapping[str, str]) -> List[Dict]:
    """Trạng thái kích hoạt toàn bộ adapter."""
    out = []
    for name in ADAPTERS:
        a = get_adapter(name, env)
        out.append(connection_test(a, env))
    return out
