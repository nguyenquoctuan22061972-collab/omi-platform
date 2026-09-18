# Disaster Recovery Drill — OMI Platform (PRD-006 F)

Diễn tập DR định kỳ (khuyến nghị hàng quý) để xác nhận RPO≤24h / RTO≤1h (xem
`disaster-recovery.md`).

## Kịch bản diễn tập
1. **Mất dữ liệu:** trên staging, xoá `./data` → `restore.sh` bản backup gần nhất →
   healthcheck + đối chiếu số liệu KPI.
2. **Mất host:** provision host mới → clone repo → `.env` từ secret store → `up -d` →
   restore → healthcheck.
3. **Rollback deploy:** deploy tag lỗi (giả lập) → thực hiện rollback theo decision tree.

## Bảng ghi kết quả (điền mỗi lần drill)
| Ngày | Kịch bản | RTO thực tế | RPO thực tế | Đạt? | Ghi chú |
|---|---|---|---|---|---|
| | | | | | |

## Tiêu chí PASS
- Phục hồi trong RTO; dữ liệu mất ≤ RPO.
- Healthcheck xanh sau phục hồi.
- Không thao tác thủ công ngoài runbook.

## Sau drill
Cập nhật runbook/risk nếu phát hiện lỗ hổng; lưu kết quả để audit.
