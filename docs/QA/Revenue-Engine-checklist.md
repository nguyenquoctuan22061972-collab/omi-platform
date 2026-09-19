# QA Checklist — Revenue Engine & Real Execution (PRD-010)

## Kết quả (CI-mirror cục bộ)
| Module | Suite | KQ |
|---|---|---|
| A Revenue Engine | `apps/revenue-engine/tests` | ✅ 5 |
| B Affiliate | `libs/affiliate/tests` | ✅ 6 |
| C Lead Engine | `libs/lead/tests` | ✅ 5 |
| D YouTube Runtime | `libs/youtube/tests` | ✅ 5 |
| E Content Calendar | `apps/content-factory/calendar/tests` | ✅ 5 |
| F CEO Revenue Dashboard | `apps/ceo-autopilot/tests/test_revenue_dashboard.py` | ✅ 3 |
| G Analytics | `libs/analytics/tests` | ✅ 5 |
| Regression | crm-core/integrations/queue/... | ✅ PASS |
| py_compile | toàn bộ module mới | ✅ |

## Acceptance
- [x] Additive; không đổi PRD-001..009, ADR, capability-map, naming, business logic, caller
- [x] Không gọi API/payment thật (dry-run/mock); key env-only; không hardcode
- [x] CRM mapping đúng hợp đồng PRD-001 §6 (không gọi API)
- [x] CI thêm 7 step (revenue/affiliate/lead/youtube/calendar/analytics; autopilot mở rộng) — xanh

## Chờ credential để production
Affiliate `<NET>_TRACKING_ID` · YouTube OAuth (`YOUTUBE_*`) · publish credential · payout gateway · RPM/AI cost source.
