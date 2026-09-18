# QA Checklist — Production Operations (PRD-006)

## Kết quả
- ✅ Dashboard suite **28/28 PASS** (10 PRD-004 + 18 mới cho A/B/C/E)
- ✅ Integration adapters **7/7 PASS** (`libs/integrations`)
- ✅ Regression: crm-core, auth-rbac, workflows, deploy — tất cả PASS
- ✅ `node --check` hợp lệ toàn bộ JS mới; 4 mock JSON hợp lệ
- ✅ CI cập nhật (thêm step integrations) — **không đỏ**

## Module → QA
| Module | Test | KQ |
|---|---|---|
| A Contacts | `apps/dashboard/tests/test_contacts.py` | ✅ |
| B Inbox | `apps/dashboard/tests/test_inbox.py` | ✅ |
| C Pipeline | `apps/dashboard/tests/test_pipeline.py` | ✅ |
| D Adapters | `libs/integrations/tests/test_integrations.py` | ✅ |
| E Operations | `apps/dashboard/tests/test_operations.py` | ✅ |
| F Runbook | docs additive (review) | ✅ |

## Acceptance criteria
- [x] Additive only — không sửa PRD-001..005, ADR, capability-map, naming, business logic
- [x] Không đổi API hiện có; Operations standalone (không sửa Dashboard KPI)
- [x] Adapter env-only, dry-run, không gọi API thật, không secret literal
- [x] Mock-first cho mọi domain; integration layer sẵn để nối thật
- [x] CI xanh (build/test), lint cú pháp (node --check) PASS
- [x] Runbook mở rộng: incident, rollback tree, credential rotation, DR drill, maintenance

## Chờ credential để bật production
- Adapter (D) `send()` thật + Inbox channel (B) → cần env credential từng provider.
- WF n8n (PRD-003) bật node disabled.
- Operations (E) nối dữ liệu thật (docker/GitHub API) thay mock.

## Chạy
```bash
( cd apps/dashboard && python3 -m unittest discover -s tests -p 'test_*.py' -v )
( cd libs/integrations && python3 -m unittest discover -s tests -p 'test_*.py' -v )
```
