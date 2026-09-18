# WF002 — AI Auto-Tag & Sales Routing (n8n)

**Trạng thái:** 🟢 Importable (PRD-003 DRAFT) — chưa nối credential.
**Map PRD-001 §9:** 9.3 AI gắn tag + 9.4 Sales xử lý.

## Import
n8n UI → *Import from File* → `workflow.json`. Đặt `CRM_BASE`.

## Luồng
`Webhook(crm/new-conversation)` → `Suggest Tags(Code, mirror tagging.py)` →
`POST /contacts (merge tags)` → `Switch(route theo tag)` → `Assign(NoOp, cắm notify)`.

## Node disabled (cần secret)
- `Notify Sales (Slack)` — cần Slack credential + `SALES_SLACK_CHANNEL`. Bật sau khi gắn.

## Cần gắn khi deploy
- `CRM_BASE`, `SALES_SLACK_CHANNEL` (xem `../.env.example`).
- (Tuỳ chọn) thay `Suggest Tags` bằng AI node thật.
