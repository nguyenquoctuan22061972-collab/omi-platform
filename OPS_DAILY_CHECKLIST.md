# OPS DAILY CHECKLIST — OMI Platform (PRD-012 F)

Chạy mỗi ngày (tham chiếu `docs/Operations/maintenance-checklist.md` + `alert-policy.md`).

## Sáng (T+0)
- [ ] `scripts/production-ready.sh` — xem Score
- [ ] `curl -s https://<domain>/api/health/gateway` → `ready`
- [ ] `curl -s https://<domain>/api/health/metrics` (hoặc `/metrics`) — `omi_health_summary 1`
- [ ] `BASE=https://<domain> deploy/scripts/healthcheck.sh` xanh
- [ ] Container `docker compose ps` — tất cả healthy

## Backup & log
- [ ] Backup đêm qua có (`ls -1t backups/omi-backup-*.tar.gz | head -1`) + `.sha256`
- [ ] `deploy/backup/backup-verify.sh <latest>` PASS
- [ ] Log lỗi nginx/app: 5xx < 1%, không spike 401/403/429

## Business
- [ ] KPI dashboard cập nhật (contacts/messages/win rate)
- [ ] n8n Executions (nếu bật) không lỗi
- [ ] Audit: login/workflow_trigger/publish/rollback hợp lý

## Alert
- [ ] Không alert P1/P2 tồn đọng (`docs/Operations/alert-policy.md`)
- [ ] Alert channel (Telegram/SMTP) trạng thái đúng (enabled/dry-run)

Sự cố → `ROLLBACK_GUIDE.md` / `DISASTER_RECOVERY.md`.
