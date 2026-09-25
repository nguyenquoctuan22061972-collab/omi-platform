"""ZALO OA Pipeline (PR-001). End-to-end dry-run: Webhook → CRM → AI → Zalo Reply.

REUSE (không fork): libs/integrations/zalo_oa.ZaloOaAdapter (dry-run send),
libs/ai_router.AIRouter (chọn provider + fallback). CRM/Audit/Metrics mô tả dạng
'would_post' tới crm_base (không gọi mạng ở dry-run).

Chỉ 2 secret để GO-LIVE: ZALO_OA_ID, ZALO_OA_ACCESS_TOKEN (đọc từ env, không hardcode).
Mọi thứ khác tự scaffold. KHÔNG network — an toàn để QA.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Mapping, Optional

# Reuse module đã build.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from libs.integrations.zalo_oa import ZaloOaAdapter          # noqa: E402
from libs.ai_router.router import AIRouter                    # noqa: E402

FALLBACK_REPLY = "Cảm ơn bạn đã nhắn tin cho OA. Chúng tôi sẽ phản hồi trong giây lát."


def parse_event(event: Dict) -> Dict:
    """Rút user_id + text từ Zalo OA webhook event (chịu vài dạng khác nhau)."""
    sender = ""
    if isinstance(event.get("sender"), dict):
        sender = event["sender"].get("id", "")
    sender = sender or event.get("user_id", "")
    msg = event.get("message") or {}
    text = msg.get("text", "") if isinstance(msg, dict) else ""
    return {"user_id": sender, "text": text}


def build_reply(text: str, env: Mapping[str, str]) -> Dict:
    """Sinh reply qua AIRouter (dry-run). Không có provider → fallback canned."""
    router = AIRouter(env)
    provider = router.select()
    if provider:
        reply = f"[AI/{provider}] Đã nhận: {text[:120]}"
    else:
        reply = FALLBACK_REPLY
    return {"provider": provider or "fallback", "reply": reply}


def handle_inbound(event: Dict, env: Optional[Mapping[str, str]] = None,
                   crm_base: str = "http://crm-core:8080") -> Dict:
    """Chạy pipeline dry-run. Trả trace từng bước + cờ ready_to_go_live."""
    env = env or {}
    steps: List[Dict] = []

    # 1. Parse (Webhook payload)
    p = parse_event(event)
    if not p["user_id"] or not p["text"]:
        return {"ok": False, "error": "invalid_event: thiếu user_id/text", "steps": steps}
    steps.append({"step": "parse", "ok": True, "user_id": p["user_id"]})

    # 2. CRM upsert (would_post — reuse endpoint crm-core /conversations)
    crm_payload = {"contact": {"zalo_user_id": p["user_id"]}, "channel": "zalo", "message": p["text"]}
    steps.append({"step": "crm", "would_post": f"{crm_base}/conversations", "payload": crm_payload})

    # 3. AI reply (reuse AIRouter, dry-run + fallback)
    ai = build_reply(p["text"], env)
    steps.append({"step": "ai", "provider": ai["provider"], "reply": ai["reply"]})

    # 4. Zalo reply (reuse ZaloOaAdapter, dry-run)
    z = ZaloOaAdapter(env)
    payload = {"recipient": {"user_id": p["user_id"]}, "message": {"text": ai["reply"]}}
    send = z.send(payload)
    steps.append({"step": "zalo_reply", "configured": z.is_configured(), "result": dict(send)})

    # 5. Audit + Metrics (would_post)
    steps.append({"step": "audit", "would_post": f"{crm_base}/audit",
                  "payload": {"event": "workflow_activation", "actor": "zalo_pipeline"}})
    steps.append({"step": "metrics", "would_post": f"{crm_base}/metrics/ingest",
                  "payload": {"metric": "workflow_count", "workflow": "WF005", "value": 1}})

    return {
        "ok": True,
        "user_id": p["user_id"],
        "reply": ai["reply"],
        "steps": steps,
        "ready_to_go_live": z.is_configured(),   # chỉ cần 2 secret Zalo là go-live được
        "zalo_missing_env": z.health()["missing_env"],
    }
