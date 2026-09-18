# WF001 — Lead Ingestion (n8n)

**Trạng thái:** 🟢 Importable (PRD-003 DRAFT) — chưa nối credential.
**Map PRD-001 §9:** 9.1 Lead vào từ nhiều kênh + 9.2 Merge theo phone/email.

## Import
n8n UI → *Import from File* → `workflow.json`. Đặt biến môi trường n8n `CRM_BASE`
(URL CRM Core).

## Luồng
`Webhook(crm/lead)` → `Normalize(Code)` → `POST /contacts` → `POST /messages` → `Respond`.

## Cần gắn khi deploy (ngoài scope B)
- `CRM_BASE`.
- Credential kênh nếu nhận trực tiếp từ FB/Zalo/Telegram (thay/nối trước Webhook).
