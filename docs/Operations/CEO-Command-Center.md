# CEO Command Center — OMI Platform (PRD-007 F)

Bảng điều khiển vận hành cấp CEO. Mỗi mục là quy trình 1 trang, gọn để hành động.

## 1. Daily Startup
1. Mở Operations dashboard (`apps/dashboard/operations/`).
2. `scripts/production-ready.sh` → xem Score.
3. Kiểm: container health xanh, backup đêm qua OK, CI xanh.

## 2. Morning Brief (5 phút)
- KPI hôm qua: Dashboard KPI (contacts, messages, win rate).
- Pipeline: số deal theo stage, deal `won`/`lost`.
- Sự cố/alert đêm qua (alert history).
- Việc cần duyệt (deploy chờ approval).

## 3. Incident Response
- Theo `incident-playbook.md`: phân loại SEV → giảm thiểu → khắc phục → postmortem.
- SEV1/2: kích hoạt on-call ngay.

## 4. Deploy Approval
- Deploy chạy qua GitHub Actions `Deploy (manual)` + Environment `production` (cần CEO/CTO approve).
- Trước approve: CI xanh, `production-ready.sh` Score cao, rollback tag sẵn.

## 5. KPI Review (tuần)
- So sánh xu hướng win rate, tổng contact/messages.
- Đối chiếu mục tiêu (Product/metrics).

## 6. Emergency Rollback
- Một lệnh: `deploy/rollback.sh <tag_tốt_trước>` (tự healthcheck).
- Dữ liệu hỏng: `deploy/scripts/restore.sh <backup>`.
- n8n lỗi: `deploy/n8n/rollback.md`.

## Lệnh nhanh
| Việc | Lệnh |
|---|---|
| Kiểm tình trạng | `scripts/production-ready.sh` |
| Go-live | `deploy/go-live.sh <tag>` |
| Rollback | `deploy/rollback.sh <tag>` |
| Healthcheck | `BASE=https://<domain> deploy/scripts/healthcheck.sh` |
| Backup | `deploy/scripts/backup.sh` |
