# Disaster Recovery — OMI Platform (PRD-005)

## Mục tiêu
- **RPO** (mất dữ liệu tối đa): ≤ 24h (backup hằng ngày; tăng tần suất nếu cần).
- **RTO** (thời gian phục hồi): ≤ 1h.

## Kịch bản & phục hồi
| Sự cố | Hành động |
|---|---|
| Container/app hỏng | `docker compose up -d` service lỗi; healthcheck |
| Mất dữ liệu / corrupt SQLite | `restore.sh` bản backup gần nhất → healthcheck |
| Mất toàn bộ host | Provision host mới → clone repo → `.env` từ secret store → `up -d` → restore backup |
| SSL/domain lỗi | certbot re-issue; kiểm tra DNS + port 80 |
| Lộ secret | Xoay `AUTH_SECRET` + credential; buộc re-login; audit |

## Quy trình phục hồi host mới
```bash
git clone <repo> && cd omi-platform
cp deploy/.env.example deploy/.env   # điền từ secret store
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d
deploy/scripts/restore.sh ./backups/omi-backup-<ts>.tar.gz
deploy/scripts/healthcheck.sh
```

## Kiểm thử DR (bắt buộc định kỳ)
- Hàng quý: khôi phục backup vào môi trường staging, xác nhận số liệu + healthcheck.
- Ghi lại thời gian phục hồi thực tế so với RTO.

## Sau sự cố
Viết postmortem (`incident-postmortem`), cập nhật runbook/risk nếu cần.
