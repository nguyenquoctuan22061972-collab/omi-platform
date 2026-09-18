# QA Checklist — Credential Activation & Go-Live (PRD-007)

## Kết quả
- ✅ Deploy suite **23/23 PASS** (15 PRD-005 + 8 phase-7 kit)
- ✅ Integrations suite **15/15 PASS** (7 adapters + 8 activation)
- ✅ Regression: crm-core, auth-rbac, workflows, dashboard — tất cả PASS
- ✅ `bash -n` (lint) sạch trên toàn bộ script; `validate-env.sh` đúng 3 kịch bản
- ✅ `production-ready.sh` sinh báo cáo PASS/FAIL + Score

## Module → QA
| Module | Test/Chứng cứ | KQ |
|---|---|---|
| A Credential Loader | `deploy/tests/test_activation_kit.py` (secrets) + chạy 3 kịch bản | ✅ |
| B Adapter Activation | `libs/integrations/tests/test_activation.py` (8 test) | ✅ |
| C n8n Kit | test_activation_kit (n8n docs) | ✅ |
| D Zero-Downtime | test_activation_kit (scripts + stages + bash -n) | ✅ |
| E Production Verify | test_activation_kit (production-ready.sh) + demo report | ✅ |
| F CEO Command Center | doc review | ✅ |

## Acceptance
- [x] Additive; không đổi PRD-001..006, ADR, capability-map, naming, business logic
- [x] Không đổi interface adapter (activation ở file mới `activation.py`)
- [x] Không gọi API thật — mọi adapter dry-run; fail-safe khi disabled/thiếu env
- [x] Không secret literal trong repo; validate-env không in giá trị
- [x] CI xanh (build/test); production-ready.sh KHÔNG là cổng CI (script vận hành)

## Chạy
```bash
( cd deploy && python3 -m unittest discover -s tests -p 'test_*.py' -v )
( cd libs/integrations && python3 -m unittest discover -s tests -p 'test_*.py' -v )
scripts/production-ready.sh          # báo cáo PASS/FAIL + Score
```
