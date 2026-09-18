# Incident Playbook — OMI Platform (PRD-006 F)

## Mức độ (severity)
| Sev | Định nghĩa | Phản hồi |
|---|---|---|
| SEV1 | Toàn hệ thống down / mất dữ liệu | Ngay lập tức, huy động on-call |
| SEV2 | 1 service down / lỗi nghiêm trọng | ≤ 30 phút |
| SEV3 | Suy giảm, workaround được | ≤ 4 giờ |

## Quy trình
1. **Phát hiện:** alert/healthcheck fail → xác nhận (`healthcheck.sh`, `docker compose ps`).
2. **Phân loại** severity.
3. **Khoanh vùng:** service nào (`logs`), ảnh hưởng người dùng.
4. **Giảm thiểu:** restart service / rollback / restore backup (theo decision tree).
5. **Khắc phục** căn nguyên.
6. **Xác nhận:** healthcheck xanh, theo dõi.
7. **Postmortem** (SEV1/2): nguyên nhân, timeline, hành động phòng ngừa.

## Liên hệ nhanh
- Runbook vận hành: `production-runbook.md`
- Rollback: `rollback-decision-tree.md`
- DR: `disaster-recovery.md` + `dr-drill.md`
