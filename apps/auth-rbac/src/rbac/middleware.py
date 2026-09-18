"""RBAC middleware (PRD-002 §3 RBAC Middleware).

Đọc access token (JWT), lấy roles, kiểm tra permission. Framework-agnostic:
- `authenticate(token, secret)` → claims (raise trên token sai/hết hạn).
- `check_permission(claims, permission)` → bool.
- `require_permission(...)` → raise Unauthorized/Forbidden để tầng API map 401/403.
"""
from __future__ import annotations

from typing import Dict

from auth import jwt_util
from rbac import matrix


class Unauthorized(Exception):
    """Chưa xác thực / token sai / hết hạn → 401."""


class Forbidden(Exception):
    """Đã xác thực nhưng thiếu quyền → 403."""


def authenticate(token: str, secret: str) -> Dict:
    if not token:
        raise Unauthorized("missing token")
    try:
        return jwt_util.decode(token, secret)
    except jwt_util.JWTError as e:
        raise Unauthorized(str(e))


def check_permission(claims: Dict, permission: str) -> bool:
    return matrix.has_permission(claims.get("roles", []), permission)


def require_permission(token: str, secret: str, permission: str) -> Dict:
    """Trả claims nếu đủ quyền; raise Unauthorized/Forbidden nếu không."""
    claims = authenticate(token, secret)
    if not check_permission(claims, permission):
        raise Forbidden(f"missing permission: {permission}")
    return claims


def bearer_from_header(authorization: str) -> str:
    """Tách token từ header 'Authorization: Bearer <token>'."""
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""
