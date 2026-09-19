"""Capability Registry v2 (PRD-014 A).

Registry giàu metadata cho capability: version (semver a.b.c), tags, deprecated, mô tả.
Hỗ trợ version constraint ('latest' | 'x.y' | '>=x.y') và bridge sang CapabilityDispatcher
(PRD-013 C) để tái dùng lookup/fallback/tracing — KHÔNG fork dispatcher.

KHÔNG đọc/sửa docs/CTO-Bible/capability-map.md (đó là tài liệu, không phải runtime).
Thuần stdlib, handler do bên ngoài inject (không hardcode business logic).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple


def _ver_key(v: str) -> Tuple:
    out = []
    for p in str(v).split("."):
        out.append(int(p) if p.isdigit() else 0)
    return tuple(out)


class CapabilitySpec:
    def __init__(self, name: str, handler: Callable, version: str = "1.0",
                 tags: Optional[List[str]] = None, deprecated: bool = False,
                 description: str = ""):
        self.name = name
        self.handler = handler
        self.version = version
        self.tags = list(tags or [])
        self.deprecated = deprecated
        self.description = description

    def to_dict(self) -> Dict:
        return {"name": self.name, "version": self.version, "tags": self.tags,
                "deprecated": self.deprecated, "description": self.description}


class CapabilityRegistryV2:
    def __init__(self) -> None:
        self._reg: Dict[str, Dict[str, CapabilitySpec]] = {}   # name -> version -> spec

    # ---- register ----
    def register(self, name: str, handler: Callable, version: str = "1.0",
                 tags: Optional[List[str]] = None, deprecated: bool = False,
                 description: str = "") -> CapabilitySpec:
        spec = CapabilitySpec(name, handler, version, tags, deprecated, description)
        self._reg.setdefault(name, {})[version] = spec
        return spec

    def deprecate(self, name: str, version: str) -> None:
        if name in self._reg and version in self._reg[name]:
            self._reg[name][version].deprecated = True

    # ---- query ----
    def has(self, name: str) -> bool:
        return name in self._reg and bool(self._reg[name])

    def versions(self, name: str, include_deprecated: bool = True) -> List[str]:
        specs = self._reg.get(name, {})
        vs = [v for v, s in specs.items() if include_deprecated or not s.deprecated]
        return sorted(vs, key=_ver_key)

    def resolve(self, name: str, constraint: Optional[str] = None) -> str:
        """constraint: None/'latest' -> version cao nhất KHÔNG deprecated (fallback: cao nhất);
        'x.y' -> đúng version; '>=x.y' -> cao nhất thỏa."""
        if not self.has(name):
            raise LookupError(f"capability không tồn tại: {name}")
        if constraint and constraint.startswith(">="):
            floor = _ver_key(constraint[2:].strip())
            cands = [v for v in self.versions(name) if _ver_key(v) >= floor]
            if not cands:
                raise LookupError(f"{name} không có version thỏa {constraint}")
            return cands[-1]
        if constraint and constraint not in (None, "latest"):
            if constraint not in self._reg[name]:
                raise LookupError(f"{name} không có version {constraint}")
            return constraint
        # latest: ưu tiên non-deprecated
        active = self.versions(name, include_deprecated=False)
        return (active or self.versions(name))[-1]

    def get(self, name: str, constraint: Optional[str] = None) -> CapabilitySpec:
        v = self.resolve(name, constraint)
        return self._reg[name][v]

    def list(self, tag: Optional[str] = None, include_deprecated: bool = False) -> List[Dict]:
        out = []
        for name, specs in sorted(self._reg.items()):
            for v in sorted(specs, key=_ver_key):
                s = specs[v]
                if not include_deprecated and s.deprecated:
                    continue
                if tag and tag not in s.tags:
                    continue
                out.append(s.to_dict())
        return out

    # ---- bridge (reuse dispatcher PRD-013 C) ----
    def to_dispatcher(self, dispatcher, include_deprecated: bool = False) -> None:
        """Nạp toàn bộ spec vào một CapabilityDispatcher để tái dùng lookup/fallback/trace."""
        for name, specs in self._reg.items():
            for v, s in specs.items():
                if not include_deprecated and s.deprecated:
                    continue
                dispatcher.register(name, s.handler, version=v)

    def stats(self) -> Dict:
        total = sum(len(v) for v in self._reg.values())
        deprecated = sum(1 for specs in self._reg.values() for s in specs.values() if s.deprecated)
        return {"capabilities": len(self._reg), "versions": total, "deprecated": deprecated}
