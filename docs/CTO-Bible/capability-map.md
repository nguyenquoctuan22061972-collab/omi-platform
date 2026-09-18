# Capability Map — OMI Platform

Bản đồ chức năng đã có (chống trùng lặp — luật #4). **Tra file này trước khi thêm mới.**

## Đã hiện thực (có code + test)
| Capability | Module | Vị trí | PRD |
|---|---|---|---|
| Lưu trữ SQLite + schema | crm-db | `apps/crm-core/src/crm/db.py`, `models.py` | PRD-001 §7 |
| Tạo/đọc contact + **merge phone/email** | crm-contacts | `contacts.py` | PRD-001 §9.2 |
| Ghi message đúng contact + timeline | crm-conversations | `conversations.py` | PRD-001 §6 |
| Cập nhật pipeline (6 stage) | crm-pipeline | `pipeline.py` | PRD-001 §6,§7 |
| Auto-tag (rule-based, cắm AI) | crm-tagging | `tagging.py` | PRD-001 §9.3 |
| KPI realtime | crm-dashboard | `dashboard.py` | PRD-001 §5,§10 |
| Ingest 6 kênh | crm-ingestion | `ingestion.py` | PRD-001 §4 |
| REST API 5 endpoint | crm-api | `api.py` | PRD-001 §6 |

## Placeholder (chưa hiện thực — cần PRD/TechSpec)
| Capability | Vị trí | Điều kiện |
|---|---|---|
| n8n Lead Ingestion | `workflows/WF001` | credential + TechSpec workflow |
| n8n AI Tag & Routing | `workflows/WF002` | như trên |
| n8n Dashboard KPI Sync | `workflows/WF050` | như trên |
| Auth/RBAC (CEO/Sales/CSKH/Admin) | (chưa) | PRD/TechSpec Security |
| Rate limiting | (chưa) | giai đoạn Deployment |
| Webhook idempotency | (chưa) | TechSpec ingestion mở rộng |

## Quy tắc
Muốn thêm capability trùng dòng "Đã hiện thực" → **tái sử dụng**, không viết lại.
Thêm capability mới → tạo PRD trước, rồi cập nhật bảng này trong cùng PR.
