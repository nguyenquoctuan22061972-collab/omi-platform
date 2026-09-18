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

## Cần gắn khi deploy
- `CRM_BASE`.
- Node `Publish`: nối kênh gửi báo cáo (Email/Slack/Sheet).
