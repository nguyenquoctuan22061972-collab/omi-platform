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

### ✅ Giai đoạn 3a — Auth & RBAC (PRD-002)
JWT+refresh+bcrypt, RBAC 4 roles, audit log. 19 test PASS. **Done, đã push.**

### 🔄 Giai đoạn 3b — Automation n8n (PRD-003 DRAFT, scope B)
Workflow JSON importable WF001/WF002/WF050 + validator 5 test PASS. **Done (skeleton),
đã push.** Còn lại (ngoài scope B): credential + deploy + endpoint KPI.

### ⏭️ Tiếp theo (chờ PRD/duyệt)
- Duyệt PRD-003 + cung cấp credential/n8n để bật automation "thật" (phương án A).
- **CR CRM Core:** expose `GET /dashboard/kpi` (gap PRD-003 §11).
- **PRD-004:** Frontend (5 màn hình theo wireframe §8).
- **PRD-005:** Deployment (ASGI + Postgres + rate-limit + CI/CD).

### ⏭️ Giai đoạn 4 — Vận hành
Monitoring, runbooks, on-call (`docs/Operations/`).

## Nguyên tắc chuyển giai đoạn
Chỉ sang bước code khi PRD + TechSpec module đó đã duyệt. Mỗi module: Deliverables ·
QA · Commit hash · Risk.
