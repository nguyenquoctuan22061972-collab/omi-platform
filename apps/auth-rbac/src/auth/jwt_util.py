"""JWT HS256 bằng stdlib (PRD-002 §3 "JWT Access Token").

Hiện thực chuẩn RFC 7519 tối thiểu: header.payload.signature, ký HMAC-SHA256.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict


class JWTError(Exception):
    pass


class ExpiredToken(JWTError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def encode(payload: Dict[str, Any], secret: str, expires_in: int = 900) -> str:
    """Tạo JWT HS256. Thêm iat/exp nếu chưa có (exp = now + expires_in)."""
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    now = int(time.time())
    body.setdefault("iat", now)
    body.setdefault("exp", now + expires_in)
    seg = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}." \
          f"{_b64url(json.dumps(body, separators=(',', ':')).encode())}"
    sig = hmac.new(secret.encode(), seg.encode(), hashlib.sha256).digest()
    return f"{seg}.{_b64url(sig)}"


def decode(token: str, secret: str) -> Dict[str, Any]:
    """Verify chữ ký + exp. Lỗi → JWTError/ExpiredToken."""
    try:
        h_seg, p_seg, s_seg = token.split(".")
    except ValueError:
        raise JWTError("malformed token")
    seg = f"{h_seg}.{p_seg}"
    expected = hmac.new(secret.encode(), seg.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(s_seg)):
        raise JWTError("bad signature")
    payload = json.loads(_b64url_decode(p_seg))
    if "exp" in payload and int(time.time()) >= int(payload["exp"]):
        raise ExpiredToken("token expired")
    return payload
