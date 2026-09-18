# WF050 — Dashboard KPI Sync (n8n)

**Trạng thái:** 🟢 Importable (PRD-003 DRAFT) — chưa nối credential.
**Map PRD-001 §9:** 9.5 Dashboard cập nhật.

## Import
n8n UI → *Import from File* → `workflow.json`. Đặt `CRM_BASE`.

## Luồng
`Schedule(cron)` → `Read KPI (GET /dashboard/kpi)` → `Format(Code)` → `Publish(NoOp)`.

## ⚠️ Gap phải xử lý trước khi bật (PRD-003 §11)
CRM Core **chưa có** endpoint `GET /dashboard/kpi` (PRD-001 §6 chỉ có 5 endpoint;
`dashboard.kpi` mới là hàm module). Cần 1 CR/PRD bổ sung endpoint này rồi mới bật WF050.

## Node disabled (cần secret)
- `Send Report (Email)` — cần SMTP credential + `REPORT_FROM_EMAIL`/`REPORT_TO_EMAIL`.

## Cần gắn khi deploy
- `CRM_BASE`, `REPORT_FROM_EMAIL`, `REPORT_TO_EMAIL` (xem `../.env.example`).
- ⚠️ Bổ sung endpoint `GET /dashboard/kpi` cho CRM Core trước khi bật (gap PRD-003 §11).
