# WF004 — AI Call Intelligence · SOP (WO-015 / WO-015C v2)

**v2:** bỏ `$env` (n8n chặn "access to env vars"). Base URL nằm trong node **Config** — sửa
1 lần trong UI. Token vẫn ở credential. Repo chỉ cung cấp file import.

## A. Import workflow
1. n8n → Workflows → Import from File → `workflows/WF004.n8n.json`.
2. Thấy 9 node: Webhook → **Config** → Validation → Vertex STT → AI Summary → CRM Update → Telegram Notify → Audit → Metrics.

## B. Sửa node Config (1 lần, không secret)
Mở **Config** → điền:
- `crm_base` = `http://crm-core:8080` (đã điền sẵn; đổi nếu n8n không cùng network với crm-core).
- `vertex_stt_url` = endpoint Vertex Speech-to-Text.
- `vertex_summary_url` = endpoint Vertex summary/LLM.
- `telegram_chat_id` = chat id nhận thông báo.

## C. Gắn credential (ngoài repo — external)
1. Vertex STT + AI Summary → credential **Google API** (service account) → **bật** 2 node.
2. Telegram Notify → credential **Telegram API** (bot token) → **bật** node.

## D. Kích hoạt & test
1. Save → Activate. Webhook production: `POST /webhook/wf004-call-intelligence`.
2. Test:
```
POST https://<n8n>/webhook/wf004-call-intelligence
{ "audio_url": "https://.../call.wav", "contact": { "phone": "+8490..." }, "lang": "vi-VN" }
```
Kỳ vọng: CRM có conversation (channel=call) + Telegram nhận summary + Audit ghi + Metrics tăng.

## E. Rollback
Deactivate workflow (không xoá file). Không ảnh hưởng WF001/002/050.

## F. Bảo mật
- Không secret trong JSON. Token chỉ trong credential n8n. `crm_base` là DNS nội bộ, không phải secret.
- Cách thay thế (nếu muốn giữ `$env`): đặt `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` trên VPS rồi restart n8n.
