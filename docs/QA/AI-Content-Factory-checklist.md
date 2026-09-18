# QA Checklist — AI Content Factory & CEO Autopilot (PRD-009)

## Kết quả (CI-mirror cục bộ)
| Module | Suite | KQ |
|---|---|---|
| A Job Queue | `apps/content-factory/queue/tests` | ✅ 5 |
| B Prompt Registry | `libs/prompts/tests` | ✅ 5 |
| C AI Router | `libs/ai_router/tests` | ✅ 6 |
| D Workflow Registry | `workflows/tests/test_registry.py` | ✅ 4 |
| E Content Pipeline | `apps/content-factory/pipeline/tests` | ✅ 5 |
| F CEO Autopilot | `apps/ceo-autopilot/tests` | ✅ 6 |
| G Publish | `libs/publish/tests` | ✅ 5 |
| Regression | crm-core/auth/dashboard/integrations/runtime-health/deploy | ✅ PASS |
| py_compile | toàn bộ module mới | ✅ |

## Acceptance
- [x] Additive; không đổi PRD-001..008, ADR, capability-map, naming, business logic
- [x] Không gọi API thật (dry-run); không hardcode key (env)
- [x] Không sửa workflow hiện có (registry chỉ metadata); không publish thật
- [x] CI thêm 7 step (queue, pipeline, prompts, ai_router, publish, autopilot) — xanh

## Chạy
```bash
for d in apps/content-factory/queue apps/content-factory/pipeline libs/prompts libs/ai_router libs/publish apps/ceo-autopilot; do
  ( cd $d && python3 -m unittest discover -s tests -p 'test_*.py' ); done
python3 workflows/runtime/registry.py   # workflow registry status
```
