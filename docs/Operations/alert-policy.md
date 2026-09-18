# Alert Policy — OMI Platform (PRD-008 E)

## Severity
| Mức | Định nghĩa | Ví dụ | Phản hồi |
|---|---|---|---|
| **P1** | Ngừng dịch vụ / mất dữ liệu | toàn hệ thống down, DB corrupt | ngay, 24/7 |
| **P2** | Suy giảm nặng | 1 service down, healthcheck fail liên tục | ≤ 30 phút |
| **P3** | Suy giảm nhẹ, có workaround | 1 kênh inbox lỗi, 429 tăng | ≤ 4 giờ (giờ hành chính) |
| **P4** | Cảnh báo sớm / cosmetic | SSL sắp hết hạn, disk 70% | ≤ 2 ngày |

## Escalation
1. On-call bậc 1 (Ops) → nếu quá SLA ack → bậc 2 (CTO).
2. P1 → thông báo CEO ngay + mở incident (`incident-playbook.md`).
3. Quá 2× SLA khắc phục → escalate lên cấp cao hơn.

## Owner (RACI rút gọn)
| Loại alert | Owner | Backup |
|---|---|---|
| Hạ tầng/deploy | Ops | CTO |
| App/API | Dev | Ops |
| Bảo mật/credential | Security/CTO | Ops |
| Automation/n8n | Ops | Dev |

## Notification matrix
| Mức | Kênh |
|---|---|
| P1 | Phone/Call + Slack #incident + Email |
| P2 | Slack #incident + Email |
| P3 | Slack #ops |
| P4 | Email/nhật ký |
> Kênh thật (Slack/Email) gắn qua adapter (dry-run tới khi có credential).

## Recovery checklist
- [ ] Ack alert + phân loại severity
- [ ] Khoanh vùng (logs, healthcheck, metrics)
- [ ] Giảm thiểu (restart/rollback/restore theo runbook)
- [ ] Xác nhận phục hồi (healthcheck xanh, metrics bình thường)
- [ ] Đóng alert + postmortem (P1/P2)
