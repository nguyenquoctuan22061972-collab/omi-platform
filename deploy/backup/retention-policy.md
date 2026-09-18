# Backup Retention Policy — OMI Platform (PRD-008 F)

## Chính sách
| Loại | Tần suất | Giữ | Nơi lưu |
|---|---|---|---|
| Daily | hằng ngày | 14 bản (`BACKUP_KEEP=14`) | `./backups` (local volume) |
| Weekly | Chủ nhật | 8 tuần | off-site (khuyến nghị: object storage) |
| Monthly | ngày 1 | 12 tháng | off-site |

## Quy trình
1. Tạo backup: `deploy/scripts/backup.sh` (đã có; xoay giữ N bản daily).
2. **Verify** ngay sau tạo: `deploy/backup/backup-verify.sh <archive>` (checksum + toàn vẹn).
3. **Restore test** định kỳ (hàng quý — DR drill): `deploy/backup/restore-verify.sh <archive>` (dry-run).
4. Sao off-site cho weekly/monthly (ngoài repo — cấu hình hạ tầng).

## Nguyên tắc
- Mọi backup có sidecar `.sha256`.
- Không commit file backup vào repo (đã gitignore `deploy/backups/`).
- Restore thật chỉ qua `deploy/scripts/restore.sh` (có sao lưu data hiện tại trước).
- RPO ≤ 24h / RTO ≤ 1h (xem `docs/Operations/disaster-recovery.md`).
