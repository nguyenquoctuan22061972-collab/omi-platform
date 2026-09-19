"""Capability Dispatcher (PRD-013 C). Chọn capability đã ĐĂNG KÝ (inject) để chạy.

- capability lookup
- version resolution (chỉ định rõ, hoặc 'latest')
- fallback strategy (thử capability dự phòng khi thiếu)
- execution tracing (ghi lại từng bước chọn)

KHÔNG hardcode business logic: mọi handler do bên ngoài register vào. Không đọc/không sửa
capability-map.md (đó là tài liệu, không phải runtime registry).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ver_key(v: str) -> Tuple:
    """Sắp version dạng 'a.b.c' → tuple số để so sánh 'latest'."""
    parts = []
    for p in str(v).split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return tuple(parts)


class CapabilityNotFound(LookupError):
    pass


class CapabilityDispatcher:
    def __init__(self) -> None:
        # {name: {version: handler}}
        self._reg: Dict[str, Dict[str, Callable]] = {}
        self.trace: List[Dict] = []

    # ---- registry (inject) ----
    def register(self, name: str, handler: Callable, version: str = "1.0") -> None:
        self._reg.setdefault(name, {})[version] = handler

    def has(self, name: str, version: Optional[str] = None) -> bool:
        if name not in self._reg:
            return False
        return version is None or version in self._reg[name]

    def versions(self, name: str) -> List[str]:
        return sorted(self._reg.get(name, {}).keys(), key=_ver_key)

    # ---- resolution ----
    def resolve_version(self, name: str, version: Optional[str] = None) -> str:
        if name not in self._reg or not self._reg[name]:
            raise CapabilityNotFound(f"capability không tồn tại: {name}")
        if version is None or version == "latest":
            return self.versions(name)[-1]     # cao nhất
        if version not in self._reg[name]:
            raise CapabilityNotFound(f"{name} không có version {version}")
        return version

    def lookup(self, name: str, version: Optional[str] = None) -> Tuple[str, Callable]:
        v = self.resolve_version(name, version)
        return v, self._reg[name][v]

    # ---- dispatch (có fallback + tracing) ----
    def dispatch(self, name: str, version: Optional[str] = None,
                 fallback: Optional[str] = None) -> Tuple[str, str, Callable]:
        """Trả (capability_name, resolved_version, handler). Ghi trace. Fallback nếu thiếu."""
        step = {"ts": _now(), "requested": name, "version": version, "fallback_used": False}
        try:
            v, handler = self.lookup(name, version)
            step.update({"resolved": name, "resolved_version": v})
            self.trace.append(step)
            return name, v, handler
        except CapabilityNotFound as e:
            step["error"] = str(e)
            if fallback and self.has(fallback):
                v, handler = self.lookup(fallback)
                step.update({"fallback_used": True, "resolved": fallback, "resolved_version": v})
                self.trace.append(step)
                return fallback, v, handler
            self.trace.append(step)
            raise

    def last_trace(self) -> Optional[Dict]:
        return self.trace[-1] if self.trace else None
