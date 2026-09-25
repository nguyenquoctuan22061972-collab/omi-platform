"""Zalo Production Activation Wizard (PR-005.1). Chuẩn bị go-live KHÔNG cần OA token thật.

Reuse (no fork): libs/integrations/zalo_oa.ZaloOaAdapter (health/dry-run send).
Tất cả offline: validate OA_ID, dry-run OpenAPI, credential health, webhook verify,
checklist generator, recovery playbook. Không network.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Dict, List, Mapping, Optional
from urllib.parse import urlparse

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from libs.integrations.zalo_oa import ZaloOaAdapter   # noqa: E402

ZALO_SEND_URL = "https://openapi.zalo.me/v3.0/oa/message"
_OA_ID_RE = re.compile(r"^\d{6,20}$")   # Zalo OA id: chuỗi số dài


def validate_oa_id(oa_id: str) -> Dict:
    """OA_ID hợp lệ = chuỗi số 6–20 ký tự."""
    ok = bool(oa_id) and bool(_OA_ID_RE.match(oa_id or ""))
    return {"check": "oa_id_format", "ok": ok,
            "reason": "" if ok else "OA_ID phải là chuỗi số 6–20 ký tự"}


def dry_run_openapi(env: Mapping[str, str], text: str = "ping") -> Dict:
    """Dựng request tới OpenAPI (KHÔNG gửi). Che token."""
    adapter = ZaloOaAdapter(env)
    spec = {
        "method": "POST", "url": ZALO_SEND_URL,
        "headers": {"Content-Type": "application/json",
                    "access_token": "***set-in-credential***"},
        "body": {"recipient": {"user_id": "<user_id>"}, "message": {"text": text}},
    }
    return {"check": "openapi_dry_run", "ok": True, "configured": adapter.is_configured(),
            "request": spec, "note": "dry-run — chưa gọi API thật"}


def credential_health(env: Mapping[str, str]) -> Dict:
    """Sức khoẻ credential Zalo (reuse adapter.health)."""
    h = ZaloOaAdapter(env).health()
    return {"check": "credential_health", "ok": h["configured"],
            "missing_env": h["missing_env"], "mode": h["mode"]}


def verify_webhook(base_url: str, path: str = "/webhook/wf005-zalo-inbound") -> Dict:
    """Xác minh URL webhook (static): https + host + path chuẩn."""
    u = urlparse(base_url or "")
    https = u.scheme == "https"
    has_host = bool(u.netloc)
    prod_url = f"{base_url.rstrip('/')}{path}" if (https and has_host) else ""
    ok = https and has_host
    return {"check": "webhook_verify", "ok": ok, "https": https, "host_ok": has_host,
            "production_url": prod_url,
            "reason": "" if ok else "base_url phải là https://<host>"}


def generate_checklist(env: Mapping[str, str], base_url: str = "") -> List[Dict]:
    oa = validate_oa_id(env.get("ZALO_OA_ID", ""))
    cred = credential_health(env)
    wh = verify_webhook(base_url) if base_url else {"check": "webhook_verify", "ok": False,
                                                    "reason": "chưa cung cấp base_url"}
    return [
        {"step": 1, "name": "OA_ID format", "status": "PASS" if oa["ok"] else "TODO", "detail": oa.get("reason", "")},
        {"step": 2, "name": "ACCESS_TOKEN credential", "status": "PASS" if cred["ok"] else "TODO",
         "detail": ",".join(cred["missing_env"])},
        {"step": 3, "name": "OpenAPI dry-run", "status": "PASS", "detail": "request build OK"},
        {"step": 4, "name": "Webhook URL", "status": "PASS" if wh["ok"] else "TODO", "detail": wh.get("reason", "")},
        {"step": 5, "name": "Enable 3 credential nodes", "status": "MANUAL", "detail": "trong n8n sau khi có credential"},
        {"step": 6, "name": "Activate WF005", "status": "MANUAL", "detail": "sau khi 1–5 PASS"},
    ]


def recovery_playbook() -> List[str]:
    return [
        "1. Lỗi gửi Zalo (401/403): kiểm ACCESS_TOKEN credential còn hạn; refresh token OA.",
        "2. Webhook 404: WF005 chưa Activate hoặc sai path /webhook/wf005-zalo-inbound.",
        "3. CRM node đỏ: n8n không cùng network với crm-core → sửa Config.crm_base.",
        "4. Rate-limited: giảm tải hoặc tăng rate_limit_per_min; token-bucket tự hồi.",
        "5. Double-message: idempotency (event_id) đã chặn; kiểm Zalo msg_id có gửi kèm.",
        "6. Rollback: Deactivate WF005 (không xoá); ghi RollbackLog; điều tra Executions.",
    ]


def run(env: Optional[Mapping[str, str]] = None, base_url: str = "") -> Dict:
    env = env or {}
    checks = [validate_oa_id(env.get("ZALO_OA_ID", "")), credential_health(env),
              dry_run_openapi(env), verify_webhook(base_url) if base_url
              else {"check": "webhook_verify", "ok": False, "reason": "no base_url"}]
    # go-live cần: OA_ID hợp lệ + credential đủ (2 secret). Webhook/base_url là bước cấu hình.
    ready = checks[0]["ok"] and checks[1]["ok"]
    return {"ready_to_activate": ready, "checks": checks,
            "checklist": generate_checklist(env, base_url), "recovery": recovery_playbook()}
