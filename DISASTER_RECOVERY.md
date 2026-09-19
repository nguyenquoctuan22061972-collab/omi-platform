# DISASTER RECOVERY — OMI Platform (PRD-012 F)

Tổng hợp DR cấp gốc. Chi tiết: `docs/Operations/disaster-recovery.md` + `docs/Operations/dr-drill.md`.

## Mục tiêu
- **RPO ≤ 24h** (backup hằng ngày `deploy/backup/daily-backup.sh`).
- **RTO ≤ 1h**.

## Kịch bản → hành động
| Sự cố | Hành động |
|---|---|
| App/container hỏng | `docker compose up -d` service lỗi → healthcheck |
| Dữ liệu corrupt/mất | `deploy/backup/backup-verify.sh <bk>` → `deploy/scripts/restore.sh <bk>` |
| Mất host | provision mới → clone → `deploy/.env` từ secret store → `deploy/go-live.sh <tag>` → restore |
| Deploy lỗi | `deploy/rollback.sh <tag_tốt>` |
| SSL/domain | certbot re-issue; kiểm DNS + port 80 |
| Lộ secret | xoay theo `docs/Operations/credential-rotation.md` |

## Quy trình host mới (tóm tắt)
```bash
git clone <repo> && cd omi-platform
cp deploy/.env.example deploy/.env   # điền từ secret store
bash deploy/go-live.sh <tag>
bash deploy/scripts/restore.sh ./backups/omi-backup-<ts>.tar.gz
BASE=https://<domain> deploy/scripts/healthcheck.sh
```

## Kiểm thử
DR drill hàng quý (`docs/Operations/dr-drill.md`) — ghi RTO/RPO thực tế.
