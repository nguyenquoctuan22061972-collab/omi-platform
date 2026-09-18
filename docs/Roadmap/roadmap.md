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

### ✅ Giai đoạn 4 — Frontend Dashboard (PRD-004) + CR-001
- CR-001: CRM Core `GET /dashboard/kpi` (backward compatible, 17 test PASS) → **gỡ gap WF050**.
- PRD-004: Dashboard vanilla JS (KPI + pipeline chart), responsive, 10/10 TC PASS.
- **Done, đã push.**

### ✅ Giai đoạn 5 — Production Deployment (PRD-005)
Docker Compose + Nginx (SSL/rate-limit/CORS/CSP/headers) + CI/CD (build/test auto,
deploy manual) + secrets + backup/restore + healthcheck + runbook + DR + security
hardening. 15/15 TC PASS, CI mirror xanh. **Done, đã push.**

### ⏭️ Tiếp theo (chờ PRD/duyệt)
- Bật automation "thật" (phương án A): credential/n8n + bật node disabled (WF050 đã sẵn sàng nhờ CR-001).
- Hoàn thiện màn Contacts/Inbox/Pipeline (skeleton → đầy đủ).
- Khi tải cao: chuyển SQLite → Postgres (ADR mới), cân nhắc Kubernetes.

### ⏭️ Giai đoạn 4 — Vận hành
Monitoring, runbooks, on-call (`docs/Operations/`).

## Nguyên tắc chuyển giai đoạn
Chỉ sang bước code khi PRD + TechSpec module đó đã duyệt. Mỗi module: Deliverables ·
QA · Commit hash · Risk.
