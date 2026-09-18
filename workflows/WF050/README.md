# WF050 — Dashboard KPI Sync (n8n)

**Trạng thái:** 🟢 Importable (PRD-003 DRAFT) — chưa nối credential.
**Map PRD-001 §9:** 9.5 Dashboard cập nhật.

## Import
n8n UI → *Import from File* → `workflow.json`. Đặt `CRM_BASE`.

## Luồng
`Schedule(cron)` → `Read KPI (GET /dashboard/kpi)` → `Format(Code)` → `Publish(NoOp)`.

## ✅ Gap đã xử lý (CR-001)
CRM Core đã có `GET /dashboard/kpi` (CR-001, backward compatible). WF050 sẵn sàng bật
sau khi gắn `CRM_BASE` + SMTP credential.

## Node disabled (cần secret)
- `Send Report (Email)` — cần SMTP credential + `REPORT_FROM_EMAIL`/`REPORT_TO_EMAIL`.

## Cần gắn khi deploy
- `CRM_BASE`, `REPORT_FROM_EMAIL`, `REPORT_TO_EMAIL` (xem `../.env.example`).
- ⚠️ Bổ sung endpoint `GET /dashboard/kpi` cho CRM Core trước khi bật (gap PRD-003 §11).
