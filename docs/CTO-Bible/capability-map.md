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
| KPI endpoint HTTP | crm-api | `apps/crm-core/src/crm/api.py` GET /dashboard/kpi | CR-001 |
| Frontend Dashboard (KPI UI) | dashboard | `apps/dashboard/*` | PRD-004 |
| Production deploy (compose/nginx/CI/CD/backup) | deploy | `deploy/*`, `.github/workflows/*` | PRD-005 |

## Importable (PRD-003 DRAFT — JSON import được, chưa nối credential)
| Capability | Vị trí | Điều kiện bật "thật" |
|---|---|---|
| n8n Lead Ingestion | `workflows/WF001/workflow.json` | credential kênh + CRM_BASE |
| n8n AI Tag & Routing | `workflows/WF002/workflow.json` | CRM_BASE + notify node |
| n8n Dashboard KPI Sync | `workflows/WF050/workflow.json` | CRM_BASE + **GET /dashboard/kpi (gap)** |

## Placeholder (chưa hiện thực — cần PRD/TechSpec)
| Capability | Vị trí | Điều kiện |
|---|---|---|
| Rate limiting | (chưa) | giai đoạn Deployment |
| Webhook idempotency | (chưa) | TechSpec ingestion mở rộng |
| Persistent refresh store (Redis/DB) | (chưa) | giai đoạn Deployment |

## AFFOS Revenue Plane (ADR-0004 · Hybrid Option C)

### Đã hiện thực [V] (có code + test)
| Capability | Vị trí | Ghi chú |
|---|---|---|
| Revenue API (ingest/approve/revoke/report/reconcile) + JWT/RBAC + 424 approval gate | `AFFOS/runtime/revenue_api.py` | reuse `apps/auth-rbac` verify |
| Durable approval + two-layer idempotency (atomic reserve) | `AFFOS/runtime/revenue_store.py` | DDL `AFFOS/core/schema/0004,0005` |
| Cost ledger (append-only trên audit_logs, ceilings) | `AFFOS/runtime/cost_ledger.py` | — |
| Provenance / proof / attribution (source-gated is_real) | `AFFOS/core/{provenance,proof}.py`, `AFFOS/core/attribution/attribution.py` | — |
| Reconciliation read-only (manual-first, D5/D8) | `AFFOS/runtime/revenue_report.py` | không mutate |
| AWIN / Impact connectors (Impact OFF) | `AFFOS/connectors/{awin,impact}` | — |

### Planned [P] (ADR-0004 — đề xuất, CHƯA triển khai)
| Capability | Decision | Trạng thái |
|---|---|---|
| Outbox table + dispatcher | D1, D7 | chưa có code |
| RevenueIngestService role (`revenue:ingest`-only) | D2 | chưa có |
| Dedicated Service Issuer + separate HS256 key | D2, D6 | chưa có; caller-auth/secret-store [B] |
| approval_id claim/lease + revoke re-check | D3 | chưa có |
| Distributed rate-limit | D4 | hiện process-local |
| Reconciliation AMBIGUOUS state | D5, D8 | chưa có |

## Quy tắc
Muốn thêm capability trùng dòng "Đã hiện thực" → **tái sử dụng**, không viết lại.
Thêm capability mới → tạo PRD trước, rồi cập nhật bảng này trong cùng PR.
