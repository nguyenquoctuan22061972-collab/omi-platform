# QA Checklist — Frontend Dashboard (PRD-004)

## Kết quả
- ✅ **10/10 validator test PASS** (`apps/dashboard/tests/test_dashboard.py`)
- ✅ `node --check` cú pháp hợp lệ trên toàn bộ JS (8 file)

## TC1-TC10 → Acceptance
| TC | Nội dung | Test | KQ |
|---|---|---|---|
| TC1 | index.html responsive (viewport) | `test_TC1_index_responsive` | ✅ |
| TC2 | root mount `#app` | `test_TC2_root_mount` | ✅ |
| TC3 | api gọi `/dashboard/kpi` (CR-001) | `test_TC3_api_calls_kpi_endpoint` | ✅ |
| TC4 | dùng config `CRM_BASE`, không hardcode host | `test_TC4_uses_config_base_no_hardcode` | ✅ |
| TC5 | mock/kpi.json hợp lệ đủ trường | `test_TC5_mock_valid` | ✅ |
| TC6 | store subscribe/set | `test_TC6_store_state_mgmt` | ✅ |
| TC7 | router có bảng route | `test_TC7_router_routes` | ✅ |
| TC8 | đủ component (nav/kpiCards/pipelineChart/overview) | `test_TC8_component_map` | ✅ |
| TC9 | không secret literal | `test_TC9_no_secret` | ✅ |
| TC10 | config.example + CSS media query | `test_TC10_config_example_and_media_query` | ✅ |

## Acceptance criteria (Definition of Done)
- [x] PRD-004 đầy đủ + TechSpec chi tiết
- [x] UI/UX responsive desktop/mobile (wireframe + CSS @media 640px)
- [x] Component map · routing (hash) · state management (store pub/sub)
- [x] Integration layer dùng `GET /dashboard/kpi` (CR-001) + mock fallback + retry
- [x] Sequence + data-flow + error handling + retry + logging (docs)
- [x] 10/10 validator PASS, JS syntax hợp lệ
- [x] Không phá PRD-001..003 (chỉ thêm apps/dashboard + CR-001 additive)

## Chạy
```bash
cd apps/dashboard && python3 -m unittest discover -s tests -p 'test_*.py' -v
cp config.example.js config.js && python3 -m http.server 8000   # xem UI
```

## Ngoài scope (sau)
Contacts/Inbox/Pipeline hiện là skeleton (PRD kế); CORS + auth khi tích hợp production.
