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
| JWT + Refresh + bcrypt | auth | `apps/auth-rbac/src/auth/*` | PRD-002 §3 |
| RBAC middleware (4 roles) | rbac | `apps/auth-rbac/src/rbac/*` | PRD-002 §3-4 |
| Audit log | auth-audit | `apps/auth-rbac/src/auth/audit.py` | PRD-002 §3 |

## Placeholder (chưa hiện thực — cần PRD/TechSpec)
| Capability | Vị trí | Điều kiện |
|---|---|---|
| n8n Lead Ingestion | `workflows/WF001` | credential + TechSpec workflow (PRD-003) |
| n8n AI Tag & Routing | `workflows/WF002` | như trên (PRD-003) |
| n8n Dashboard KPI Sync | `workflows/WF050` | như trên (PRD-003) |
| Rate limiting | (chưa) | giai đoạn Deployment |
| Webhook idempotency | (chưa) | TechSpec ingestion mở rộng |
| Persistent refresh store (Redis/DB) | (chưa) | giai đoạn Deployment |

## Quy tắc
Muốn thêm capability trùng dòng "Đã hiện thực" → **tái sử dụng**, không viết lại.
Thêm capability mới → tạo PRD trước, rồi cập nhật bảng này trong cùng PR.
