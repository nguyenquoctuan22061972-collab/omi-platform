# WF005 — Zalo OA Assistant · SOP (PR-001)

Pipeline: **Webhook → Config → Parse → CRM Update → AI Reply → Zalo Reply → Audit → Metrics** (8 node).
Config-based (không $env). GO-LIVE chỉ cần **2 secret**.

## Import & cấu hình
1. n8n → Import `workflows/WF005.n8n.json`.
2. Node **Config**: `crm_base=http://crm-core:8080` (sẵn), `zalo_oa_id` = **OA_ID** của Anh, `zalo_send_url` = `https://openapi.zalo.me/v3.0/oa/message` (sẵn).

## 2 secret (credential n8n — KHÔNG commit)
- **Zalo Reply** → credential `httpHeaderAuth`: header `access_token` = **ACCESS_TOKEN** OA → **enable** node.
- **AI Reply** → credential AI provider (tuỳ chọn) → enable; nếu chưa có, giữ disabled, pipeline vẫn chạy (CRM + audit + metrics).

## Đăng ký webhook với Zalo
- Trỏ Zalo OA webhook về: `https://<n8n>/webhook/wf005-zalo-inbound`.

## Test (dry-run trước khi live)
```
POST /webhook/wf005-zalo-inbound
{ "sender": { "id": "zalo_user_123" }, "message": { "text": "Giá gói Premium?" } }
```
Kỳ vọng: CRM có conversation (channel=zalo) → (AI reply nếu bật) → Zalo Reply gửi tin (khi đã gắn access_token).

## Rollback
Deactivate WF005 (không xoá). Không ảnh hưởng WF001/002/004/050.
