# FIRST 24H MONITORING — OMI Platform (PRD-011 F)

Theo dõi 24 giờ đầu sau go-live. Kết hợp `docs/Operations/production-runbook.md` +
`docs/Operations/alert-policy.md`.

## Nhịp kiểm
| Mốc | Việc |
|---|---|
| T+0 | `/api/health/gateway` = ready · healthcheck xanh · `scripts/production-ready.sh` Score |
| T+1h | Xem n8n Executions (nếu bật WF) · nginx 5xx/429 · container `restart` count |
| T+6h | Backup đầu tiên chạy (`deploy/scripts/backup.sh`) + verify |
| T+12h | KPI dashboard cập nhật đúng · audit log (login/refresh) hợp lý |
| T+24h | Tổng kết: lỗi/alert, điều chỉnh rate-limit nếu cần |

## Chỉ số theo dõi
- **Health:** `/health`, `/health/ready`, `/health/gateway`.
- **Errors:** tỉ lệ 5xx (< 1%), 401/403/429 bất thường.
- **Runtime:** container healthy, CPU/RAM/disk, SSL còn hạn.
- **Business:** contacts/messages tăng, KPI realtime, pipeline moves.

## Ngưỡng cảnh báo (theo alert-policy)
- P1: hệ thống down / mất dữ liệu → xử lý ngay.
- P2: 1 service down / healthcheck fail liên tục → ≤ 30 phút.
- P3: suy giảm có workaround → ≤ 4 giờ.

## Khi có sự cố
`ROLLBACK_GUIDE.md` + `docs/Operations/incident-playbook.md`. Ghi postmortem cho P1/P2.
