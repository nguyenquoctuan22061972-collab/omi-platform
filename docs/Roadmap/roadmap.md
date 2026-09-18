# Roadmap — OMI Platform

## Trạng thái theo giai đoạn

### ✅ Giai đoạn 0 — Foundation (Deliverable #1)
Scaffold tài liệu CTO, template PRD/TechSpec, QA/TestPlan/Risks. **Done, đã push.**

### ✅ Giai đoạn 1 — CRM Core (PRD-001)
TechSpec + code 9 module + REST 5 endpoint + 14 test PASS + n8n placeholders.
**Done, đã push (18 commit theo module).**

### 🔄 Giai đoạn 2 — CTO Governance Foundation (đang chạy)
- [x] `CTO-Bible/standards.md`
- [x] `CTO-Bible/capability-map.md`
- [x] `CTO-Bible/adr/ADR-0001` (stack CRM Core)
- [x] `Product/vision.md`
- [x] `Roadmap/roadmap.md`

### ⏭️ Giai đoạn 3 — Module tiếp theo (chờ PRD)
Ứng viên (cần PRD trước khi code — luật #2):
- **PRD-002:** Auth & RBAC (CEO/Sales/CSKH/Admin) — gỡ Risk "Phân quyền sai".
- **PRD-003:** Automation n8n thật (WF001/WF002/WF050) — credential + idempotency.
- **PRD-004:** Frontend (5 màn hình theo wireframe §8).
- **PRD-005:** Deployment (ASGI + Postgres + rate-limit + CI/CD).

### ⏭️ Giai đoạn 4 — Vận hành
Monitoring, runbooks, on-call (`docs/Operations/`).

## Nguyên tắc chuyển giai đoạn
Chỉ sang bước code khi PRD + TechSpec module đó đã duyệt. Mỗi module: Deliverables ·
QA · Commit hash · Risk.
