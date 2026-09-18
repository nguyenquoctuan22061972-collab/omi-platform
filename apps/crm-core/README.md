# CRM Core (PRD-001 / CRM-Core)

Lõi CRM đa kênh cho OMI Platform. Python 3.11 stdlib (không phụ thuộc mạng).

- PRD: [`../../docs/PRD/PRD-001.md`](../../docs/PRD/PRD-001.md)
- TechSpec: [`../../docs/TechSpec/CRM-Core.md`](../../docs/TechSpec/CRM-Core.md)

## Chạy
```bash
python3 apps/crm-core/run.py          # http://0.0.0.0:8080, DB file crm_core.db
CRM_DB_PATH=:memory: python3 apps/crm-core/run.py
```

## API (bám PRD §6)
| Method | Path | Mô tả |
|---|---|---|
| POST | /contacts | Tạo contact (tự merge theo phone/email) |
| GET | /contacts/{id} | Lấy hồ sơ hợp nhất |
| POST | /messages | Ghi tin nhắn gắn đúng contact |
| GET | /conversations?contact_id= | Timeline hội thoại |
| POST | /pipeline/update | Cập nhật stage (6 giá trị hợp lệ) |

## QA
```bash
cd apps/crm-core && python3 -m unittest discover -s tests -p 'test_*.py' -v
```
14 test, map đúng 4 Test Case của PRD §10. Xem [`../../docs/QA/QA-001.md`](../../docs/QA/QA-001.md).

## Cấu trúc
```
apps/crm-core/
├── run.py
├── src/crm/{db,models,contacts,conversations,pipeline,tagging,dashboard,ingestion,api}.py
└── tests/{_base,test_contacts_merge,test_conversations,test_pipeline,test_dashboard_kpi}.py
```

## Giới hạn MVP (nằm trong Risk PRD §11)
- Chưa gắn auth/RBAC (điểm cắm sẵn) — "Phân quyền sai".
- Chưa rate-limit — "Giới hạn API".
- Chưa idempotency webhook — "Mất webhook".
