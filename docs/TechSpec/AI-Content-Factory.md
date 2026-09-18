# Tech Spec — AI Content Factory & CEO Autopilot (PRD-009)

**PRD:** [`../PRD/PRD-009.md`](../PRD/PRD-009.md) · Additive; Python stdlib; dry-run.

## Thành phần
| Module | File | Ghi chú |
|---|---|---|
| Job Queue | `apps/content-factory/queue/jobqueue.py` | heapq priority, retry→dead-letter, timeline |
| Prompt Registry | `libs/prompts/registry.py` | 8 category, version list, render() |
| AI Router | `libs/ai_router/router.py` | providers env-gated, select/fallback/route (dry-run) |
| Workflow Registry | `workflows/runtime/registry.py` | metadata + đối chiếu file thực tế |
| Content Pipeline | `apps/content-factory/pipeline/pipeline.py` | 7-stage state machine, mock runner |
| CEO Autopilot | `apps/ceo-autopilot/src/autopilot.py` | integration layer, dependency-injected |
| Publish | `libs/publish/connectors.py` | 4 connector, publish() dry-run |

## Nguyên tắc
- Không network/không API thật; key qua env; mặc định tắt/dry-run.
- Interface ổn định → bật production = hiện thực hàm thật (send/route/publish) + gắn env, không đổi caller.
- Không sửa module/PRD hiện có; chỉ thêm.

## Tích hợp
Autopilot nhận dữ liệu từ CRM KPI (CR-001), queue stats, workflow registry, alerts →
tổng hợp dashboard. Content pipeline dùng Prompt Registry + AI Router (khi bật) →
Publish connectors. Điều phối qua Job Queue.

## QA/CI
7 suite mới + workflows registry test (auto). CI thêm 7 step; regression giữ nguyên → xanh.
