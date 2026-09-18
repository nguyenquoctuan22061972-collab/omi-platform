# Tech Spec — Production Deployment

**PRD:** [`../PRD/PRD-005.md`](../PRD/PRD-005.md) · **ADR:** [`../CTO-Bible/adr/ADR-0003-deployment.md`](../CTO-Bible/adr/ADR-0003-deployment.md)

## 1. Topology
3 container ứng dụng + nginx + certbot (Let's Encrypt).
```
nginx  ──> dashboard (static, mount)
       ──> crm-core:8080   (/api/crm/)
       ──> auth-rbac:8081  (/api/auth/)
certbot ──> nginx (webroot ACME + cert renew)
volumes: ./data (SQLite), ./certs (SSL), ./backups
```

## 2. Container hoá
| Service | Base image | Cmd | Port |
|---|---|---|---|
| crm-core | python:3.11-slim | `python run.py` | 8080 |
| auth-rbac | python:3.11-slim | `pip install -r requirements.txt && python run.py` | 8081 |
| dashboard | static (nginx phục vụ) | — | 80 (qua nginx) |
| nginx | nginx:alpine | reverse proxy + SSL | 80/443 |
| certbot | certbot/certbot | renew | — |

Dockerfile: `deploy/Dockerfile.<service>`. Non-root user, healthcheck.

## 3. Nginx
- Reverse proxy `/api/crm/`, `/api/auth/`; static `/`.
- SSL (Let's Encrypt); redirect 80→443.
- **Rate limit:** `limit_req_zone` 10r/s + burst.
- **CORS:** chỉ cho origin cấu hình.
- **CSP + security headers:** CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff,
  Referrer-Policy, HSTS.
Config: `deploy/nginx/nginx.conf`, `deploy/nginx/conf.d/omi.conf`.

## 4. CI/CD (GitHub Actions)
- `ci.yml` (push/PR): setup Python → cài bcrypt → chạy 4 test-suite (crm-core, auth-rbac,
  workflows, dashboard). Xanh mới merge.
- `deploy.yml` (`workflow_dispatch` thủ công): build image → (placeholder) deploy qua SSH
  compose. Không auto-deploy để tránh sự cố ngoài ý.

## 5. Secrets
`.env` (gitignored). `deploy/.env.example` liệt kê biến, **không giá trị thật**.
Trên server: đặt `.env`, hoặc dùng secret manager. GitHub: repo/environment secrets.

## 6. Backup / Restore
- `deploy/scripts/backup.sh`: tar `./data` (SQLite) + timestamp → `./backups`, giữ N bản.
- `deploy/scripts/restore.sh <file>`: dừng service → giải nén → khởi động lại.
- Lịch: cron/systemd timer (ngoài repo). Restore phải được test định kỳ (DR).

## 7. Healthcheck / Monitoring / Logging / Alerting
- Healthcheck: `deploy/scripts/healthcheck.sh` gọi `/api/crm/dashboard/kpi` + `/api/auth/...`.
- Docker healthcheck trong compose (interval/retries).
- Logging: nginx access/error; app stdout → docker logging driver; tập trung (tuỳ chọn).
- Alerting: webhook/email khi healthcheck fail hoặc CI fail (placeholder cấu hình).

## 8. Rollback
Deploy theo image tag. Rollback = `deploy.yml` với tag trước, hoặc `docker compose` pin
image cũ + `up -d`. Dữ liệu: restore backup nếu migration hỏng. Chi tiết runbook.

## 9. Security hardening
RBAC (PRD-002) + nginx rate limit/CORS/CSP/headers + non-root container + secrets ngoài
repo + HSTS/redirect HTTPS. Xem `../Security/hardening.md`.

## 10. Không phá vỡ
Chỉ thêm `deploy/`, `.github/workflows/`, docs. Không sửa code PRD-001..004 (Dockerfile
gọi run.py/config sẵn có; dashboard `config.js` đặt `CRM_BASE=/api/crm`).
