# WF004 — AI Call Intelligence · SOP (WO-015)

Quy trình vận hành để **kích hoạt** WF004 (repo chỉ cung cấp file import; bật cần credential).

## A. Import workflow
1. n8n → Workflows → Import from File → chọn `workflows/WF004.n8n.json`.
2. Kiểm tra 8 node đúng chuỗi Webhook→…→Metrics.

## B. Gắn credential (ngoài repo — external)
1. Vertex STT + AI Summary: tạo credential `Google API` (service account) → gán vào 2 node, **bật** node.
2. Telegram Notify: tạo credential `Telegram API` (bot token) → gán → **bật** node.

## C. Đặt biến môi trường (deploy/.env trên VPS — KHÔNG commit)
```
CRM_BASE=...              # nội bộ, vd http://crm-core:8080
VERTEX_STT_URL=...
VERTEX_SUMMARY_URL=...
TELEGRAM_CHAT_ID=...
```

## D. Kích hoạt
1. Bật 3 node disabled sau khi đã có credential.
2. Activate workflow. Lấy webhook URL production.

## E. Kiểm thử vận hành
```
POST https://<n8n>/webhook/wf004-call-intelligence
{ "audio_url": "https://.../call.wav", "contact": { "phone": "+8490..." }, "lang": "vi-VN" }
```
Kỳ vọng: CRM có conversation mới (channel=call) + Telegram nhận summary + audit ghi + metric tăng.

## F. Rollback
- Deactivate workflow trong n8n (không xoá file). Không ảnh hưởng WF001/002/050.

## G. Bảo mật
- Không dán token vào JSON hay chat. Credential chỉ nằm trong n8n; biến trong `deploy/.env` (gitignored).
