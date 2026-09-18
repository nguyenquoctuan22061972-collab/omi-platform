# QA Checklist — CRM Core (PRD-001)

> Tick trước khi coi module là Done. Báo cáo kết quả chạy: `QA-001.md`.

## A. Tài liệu
- [x] TechSpec `docs/TechSpec/CRM-Core.md` khớp PRD
- [x] Database schema `docs/Database/CRM-Core-schema.md` khớp `db.py`
- [x] API spec `docs/API/CRM-Core-api.md` khớp `api.py` (5 endpoint, không dư)
- [x] UI wireframe 5 màn hình `docs/Product/CRM-Core-ui-wireframes.md` (đúng §8)
- [x] Không lộ secret; không link chết

## B. Database (PRD §7)
- [x] 3 bảng contacts/conversations/pipeline đúng cột
- [x] FK bật; stage giới hạn 6 giá trị
- [x] Merge chống trùng phone/email

## C. API (PRD §6)
- [x] POST /contacts (201, merge)
- [x] GET /contacts/{id} (200/404)
- [x] POST /messages (201, đúng contact)
- [x] GET /conversations (200, lọc contact_id)
- [x] POST /pipeline/update (200; 400 stage sai)

## D. Test tự động (PRD §10)
- [x] Trùng số điện thoại phải merge — `test_contacts_merge.py`
- [x] Tin nhắn đúng contact — `test_conversations.py`
- [x] Pipeline cập nhật — `test_pipeline.py`
- [x] KPI realtime — `test_dashboard_kpi.py`
- [x] `python3 -m unittest discover -s tests` → **14/14 PASS**
- [x] Smoke test 5 endpoint qua HTTP → PASS

## E. Workflow n8n (placeholder)
- [x] WF001 Lead Ingestion (README + workflow.json skeleton)
- [x] WF002 AI Auto-Tag & Routing
- [x] WF050 Dashboard KPI Sync
- [ ] Nối credential + deploy (giai đoạn Deployment — ngoài PRD-001)

## F. Rủi ro (PRD §11)
- [x] Trùng dữ liệu → merge rule
- [ ] Giới hạn API (rate-limit) — chưa, ghi nhận
- [ ] Mất webhook (idempotency) — chưa, ghi nhận
- [ ] Phân quyền RBAC — chưa, điểm cắm sẵn

## Định nghĩa Done
File ✅ · Checklist ✅ · Test ✅ · Risk notes ✅
