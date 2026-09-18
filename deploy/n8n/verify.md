# n8n — Verify (PRD-007 C)

Xác minh sau khi enable (không gọi API thật ngoài kênh test có kiểm soát).

## WF001 Lead Ingestion
- Gửi payload test tới webhook `{{N8N_BASE_URL}}/webhook/crm/lead`:
  ```json
  { "name":"Test","phone":"0900000000","channel":"api_webhook","message":"hello" }
  ```
- Kỳ vọng: 200; CRM có contact (merge theo phone) + 1 conversation.
- Kiểm: `GET {CRM_BASE}/contacts/{id}` và `GET {CRM_BASE}/conversations`.

## WF002 Auto-Tag & Routing
- Trigger `crm/new-conversation` với message chứa từ khoá (vd "giá").
- Kỳ vọng: contact được gắn tag; node Route đi đúng nhánh; Notify (nếu bật) gửi.

## WF050 KPI Sync
- Chờ cron hoặc chạy thủ công.
- Kỳ vọng: `Read KPI` trả 200 từ `GET {CRM_BASE}/dashboard/kpi` (CR-001); report gửi (nếu bật email).

## Checklist verify
- [ ] Webhook trả 200
- [ ] CRM ghi nhận đúng (contact/conversation/tag)
- [ ] KPI đọc được
- [ ] n8n Executions không lỗi
- [ ] Không lỗi credential
> Có lỗi → `rollback.md`.
