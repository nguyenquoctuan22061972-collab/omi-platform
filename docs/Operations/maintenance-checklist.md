# Maintenance Checklist — OMI Platform (PRD-006 F)

## Hằng ngày
- [ ] Healthcheck xanh (`healthcheck.sh`)
- [ ] Backup chạy thành công (kiểm `./backups` có bản mới)
- [ ] Không alert nghiêm trọng tồn đọng

## Hằng tuần
- [ ] Xem log lỗi nginx/app (rà 5xx/429 bất thường)
- [ ] CI xanh trên `main`
- [ ] Dung lượng đĩa/volume còn đủ

## Hằng tháng
- [ ] Cập nhật base image (python-slim, nginx-alpine) + rebuild
- [ ] Rà soát dependency (bcrypt…) & vá bảo mật
- [ ] Kiểm tra SSL còn hạn (certbot renew hoạt động)

## Hằng quý
- [ ] **DR drill** (`dr-drill.md`) + ghi kết quả
- [ ] **Credential rotation** (`credential-rotation.md`)
- [ ] Rà soát RBAC & quyền người dùng
- [ ] Review capacity (cân nhắc SQLite→Postgres nếu tải tăng)

## Trước mỗi release
- [ ] `production-checklist.md` (PRD-005)
- [ ] Test-suite + validator PASS (CI xanh)
- [ ] Rollback plan sẵn sàng (tag trước)
