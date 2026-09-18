"""Ma trận role → permission (PRD-002 §4).

4 role cố định: Admin ⊇ Manager ⊇ Operator ⊇ Viewer.
Giữ ánh xạ ở code (không thêm bảng ngoài 5 bảng PRD); `permissions` DB là catalog.
"""
from __future__ import annotations

from typing import Dict, List, Set

ROLES: List[str] = ["Admin", "Manager", "Operator", "Viewer"]

# Quyền theo từng role.
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "Viewer": {"contact:read"},
    "Operator": {"contact:read", "contact:write", "pipeline:write"},
    "Manager": {"contact:read", "contact:write", "pipeline:write", "audit:read"},
    "Admin": {
        "contact:read",
        "contact:write",
        "pipeline:write",
        "audit:read",
        "user:manage",
    },
}

# Catalog toàn bộ permission (để seed bảng permissions).
ALL_PERMISSIONS: List[str] = sorted(
    {p for perms in ROLE_PERMISSIONS.values() for p in perms}
)


def permissions_for_roles(roles: List[str]) -> Set[str]:
    """Hợp permission của danh sách roles."""
    result: Set[str] = set()
    for r in roles or []:
        result |= ROLE_PERMISSIONS.get(r, set())
    return result


def has_permission(roles: List[str], permission: str) -> bool:
    return permission in permissions_for_roles(roles)
