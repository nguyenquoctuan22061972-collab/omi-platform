# ROLLBACK GUIDE — OMI Platform (PRD-011 F)

Khôi phục nhanh khi go-live/deploy lỗi. Chi tiết cây quyết định:
`docs/Operations/rollback-decision-tree.md`.

## Quyết định nhanh
```
Sự cố?
├─ Deploy vừa xong lỗi (CI/smoke fail) → deploy/rollback.sh <tag_tốt_trước>
├─ Lỗi cấu hình env → sửa deploy/.env → bash deploy/go-live.sh <tag>
├─ Dữ liệu hỏng → deploy/scripts/restore.sh <backup> → healthcheck
└─ 1 workflow n8n lỗi → deploy/n8n/rollback.md (tắt/re-import, không đụng WF khác)
```

## Lệnh
| Việc | Lệnh |
|---|---|
| Rollback image | `bash deploy/rollback.sh <tag_tốt_trước>` (tự healthcheck) |
| Restore dữ liệu | `bash deploy/scripts/restore.sh ./backups/omi-backup-<ts>.tar.gz` |
| Verify backup trước restore | `bash deploy/backup/backup-verify.sh <archive>` |
| Xác minh sau rollback | `BASE=https://<domain> deploy/scripts/healthcheck.sh` |

## Nguyên tắc
- Ưu tiên khôi phục dịch vụ trước, root-cause sau.
- Rollback theo image tag (immutable); không sửa tay trên prod.
- Chỉ restore dữ liệu khi xác nhận corrupt (tránh mất data mới).
- Ghi lại thời điểm/tag/lý do cho postmortem.
