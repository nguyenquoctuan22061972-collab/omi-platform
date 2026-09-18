"""Auth service — register/login/logout/refresh/me (PRD-002 §3)."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from auth import passwords, jwt_util, tokens, audit
from rbac import matrix


class AuthError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(conn: sqlite3.Connection, username: str, password: str, roles: List[str]) -> dict:
    """Tạo user + gán roles. Dùng cho seed/admin."""
    uid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (uid, username, passwords.hash_password(password), _now()),
    )
    from auth import db as _db
    for r in roles:
        rid = _db.role_id(conn, r)
        if rid is None:
            raise AuthError(f"role không tồn tại: {r}")
        conn.execute(
            "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", (uid, rid)
        )
    conn.commit()
    return {"id": uid, "username": username, "roles": roles}


def get_roles(conn: sqlite3.Connection, user_id: str) -> List[str]:
    rows = conn.execute(
        """SELECT r.name FROM user_roles ur
           JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = ? ORDER BY r.name""",
        (user_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _issue_access(conn, user_row, secret: str, access_ttl: int) -> str:
    roles = get_roles(conn, user_row["id"])
    return jwt_util.encode(
        {"sub": user_row["id"], "username": user_row["username"], "roles": roles},
        secret,
        expires_in=access_ttl,
    )


def login(conn, username: str, password: str, secret: str, access_ttl: int = 900) -> Dict:
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not passwords.verify_password(password, row["password_hash"]):
        audit.log(conn, "login_failed", user_id=(row["id"] if row else None),
                  detail=f"username={username}")
        raise AuthError("invalid credentials")
    access = _issue_access(conn, row, secret, access_ttl)
    refresh = tokens.issue(conn, row["id"])
    audit.log(conn, "login_success", user_id=row["id"])
    return {"access_token": access, "refresh_token": refresh,
            "token_type": "Bearer", "expires_in": access_ttl}


def refresh(conn, refresh_token: str, secret: str, access_ttl: int = 900) -> Dict:
    uid = tokens.resolve(conn, refresh_token)
    if not uid:
        audit.log(conn, "refresh_failed", detail="invalid refresh token")
        raise AuthError("invalid refresh token")
    row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    access = _issue_access(conn, row, secret, access_ttl)
    audit.log(conn, "refresh", user_id=uid)
    return {"access_token": access, "expires_in": access_ttl}


def logout(conn, refresh_token: str, user_id: str = None) -> bool:
    ok = tokens.revoke(conn, refresh_token)
    audit.log(conn, "logout", user_id=user_id, detail=f"revoked={ok}")
    return ok


def me(conn, access_token: str, secret: str) -> Dict:
    payload = jwt_util.decode(access_token, secret)  # raises on invalid/expired
    roles = payload.get("roles", [])
    return {
        "id": payload["sub"],
        "username": payload.get("username"),
        "roles": roles,
        "permissions": sorted(matrix.permissions_for_roles(roles)),
    }
