"""Password hashing bằng bcrypt (PRD-002 §3)."""
from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Trả về bcrypt hash (str) cho mật khẩu."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """So khớp mật khẩu với hash; an toàn với hash rỗng/hỏng."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
