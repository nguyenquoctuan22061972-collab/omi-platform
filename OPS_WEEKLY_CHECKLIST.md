# OPS WEEKLY CHECKLIST — OMI Platform (PRD-012 F)

Chạy hằng tuần (bổ sung cho daily).

## Hạ tầng
- [ ] Dung lượng đĩa/volume còn đủ (data + backups)
- [ ] SSL còn hạn > 20 ngày (certbot renew hoạt động)
- [ ] CI xanh trên `main` (7 ngày qua)
- [ ] Cập nhật base image nếu có vá bảo mật (python-slim, nginx-alpine)

## Dữ liệu & DR
- [ ] Restore verify 1 bản backup gần nhất (`deploy/backup/restore-verify.sh`)
- [ ] Rotation đúng (giữ N bản daily; weekly/monthly off-site nếu cấu hình)

## Observability
- [ ] Xem xu hướng metrics (`/metrics`): health_summary, queue_size, adapter_status
- [ ] Rà audit log (`libs/audit`) — bất thường login/rollback
- [ ] Log shipping hoạt động (file/DB/remote theo cấu hình)

## Bảo mật
- [ ] Rà RBAC & quyền người dùng
- [ ] Lịch credential rotation (`docs/Operations/credential-rotation.md`) — tới hạn thì xoay

## Hằng quý (nhắc)
- [ ] DR drill (`docs/Operations/dr-drill.md`)
- [ ] Review capacity (SQLite→Postgres nếu tải tăng)
