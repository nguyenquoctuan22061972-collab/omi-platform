# Production Runbook — OMI Platform (PRD-005)

## 1. Triển khai lần đầu
```bash
cp deploy/.env.example deploy/.env      # điền OMI_DOMAIN, AUTH_SECRET...
# cấp SSL lần đầu (certbot) rồi:
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d
deploy/scripts/healthcheck.sh           # xác nhận xanh
```

## 2. Cập nhật phiên bản (deploy)
- Ưu tiên qua GitHub Actions `Deploy (manual)` với `image_tag`.
- Hoặc trên server: `docker compose ... pull && up -d` rồi healthcheck.

## 3. Healthcheck
`BASE=https://<domain> deploy/scripts/healthcheck.sh` → CRM KPI 200, Auth 200/401, Dashboard 200/301.

## 4. Logging
- `docker compose logs -f nginx crm-core auth-rbac`.
- nginx access/error trong container; app stdout qua docker logging driver.

## 5. Monitoring / Alerting
- Docker healthcheck (compose) → container unhealthy tự restart (`restart: unless-stopped`).
- Cron chạy `healthcheck.sh`; fail → gửi `ALERT_WEBHOOK_URL`.
- Theo dõi 429/5xx trên nginx.

## 6. Backup / Restore
- Backup: `BACKUP_DIR=./backups deploy/scripts/backup.sh` (đặt cron hằng ngày).
- Restore: `deploy/scripts/restore.sh ./backups/omi-backup-<ts>.tar.gz`.

## 7. Rollback
1. Xác định phiên bản tốt trước đó (image tag/git sha).
2. Deploy lại tag đó (`Deploy (manual)`), hoặc pin image cũ trong compose + `up -d`.
3. Nếu dữ liệu hỏng: `restore.sh` bản backup gần nhất.
4. `healthcheck.sh` xác nhận. Ghi incident.

## 8. Sự cố thường gặp
| Triệu chứng | Xử lý |
|---|---|
| 502/504 | app container down → `logs`, `up -d`, healthcheck |
| 429 nhiều | rate limit chặn; kiểm tra tấn công / nới `limit_req` có kiểm soát |
| SSL lỗi | certbot renew; kiểm tra DNS/port 80 |
| Mất dữ liệu | restore backup (DR) |
