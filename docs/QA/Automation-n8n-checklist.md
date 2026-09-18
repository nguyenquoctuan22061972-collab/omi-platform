# QA Checklist — Automation n8n (PRD-003 DRAFT, scope B)

## Kết quả
- ✅ **5/5 validator test PASS** (`workflows/tests/test_workflows.py`)
- ✅ JSON hợp lệ, import được vào n8n (WF001/WF002/WF050)

## Map QA PRD-003 §9 → validator
| QA | Test | Kết quả |
|---|---|---|
| JSON hợp lệ, import được | `test_valid_structure` | ✅ |
| Có trigger + HTTP node | `test_has_trigger_and_http` | ✅ |
| Connection trỏ node tồn tại | `test_connections_point_to_existing_nodes` | ✅ |
| URL dùng `$env.CRM_BASE` | `test_http_urls_use_env_no_secret` | ✅ |
| Không hardcode secret | `test_no_hardcoded_secret_markers` | ✅ |

## Trạng thái workflow
| WF | Map PRD-001 §9 | Importable | Credential |
|---|---|:--:|---|
| WF001 Lead Ingestion | 9.1-9.2 | ✅ | chưa nối (scope B) |
| WF002 AI Tag & Routing | 9.3-9.4 | ✅ | chưa nối (scope B) |
| WF050 KPI Sync | 9.5 | ✅ | chưa nối; ⚠️ gap KPI endpoint |

## Lệnh chạy lại
```bash
cd workflows && python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Ngoài scope B (cần credential/n8n để hoàn tất "thật")
- [ ] Gắn credential từng kênh trong n8n
- [ ] Đặt `CRM_BASE` trỏ CRM Core đang chạy
- [ ] Bổ sung endpoint `GET /dashboard/kpi` cho CRM Core (gap PRD-003 §11) trước khi bật WF050
- [ ] Retry/backoff + idempotency webhook

## Định nghĩa Done (scope B) — đạt
File ✅ · Checklist ✅ · Test ✅ · Risk notes ✅
