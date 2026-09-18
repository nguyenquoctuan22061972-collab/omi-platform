# QA Checklist — Automation n8n (PRD-003, scope B)

## Kết quả
- ✅ **7/7 validator test PASS** (`workflows/tests/test_workflows.py`)
- ✅ 3 JSON hợp lệ, import được (WF001/WF002/WF050)

## Test cases → Acceptance criteria
| TC | Nội dung | Acceptance | Test | KQ |
|---|---|---|---|---|
| TC1 | JSON hợp lệ | 3 file parse + có name/nodes/connections | `test_TC1_valid_structure` | ✅ |
| TC2 | Trigger + HTTP | mỗi WF ≥1 trigger & ≥1 httpRequest | `test_TC2_has_trigger_and_http` | ✅ |
| TC3 | Connection | mọi đích/nguồn là node tồn tại | `test_TC3_connections_valid` | ✅ |
| TC4 | Env URL | httpRequest dùng `{{$env.CRM_BASE}}` | `test_TC4_http_uses_env` | ✅ |
| TC5 | No secret | không secret literal trong JSON | `test_TC5_no_secret_literal` | ✅ |
| TC6 | Disabled | node có credential đều `disabled` | `test_TC6_credential_nodes_disabled` | ✅ |
| TC7 | Env file | có `.env.example` + N8N_BASE_URL/CRM_BASE | `test_TC7_env_example_exists` | ✅ |

## Node cần secret → đã disabled
| WF | Node disabled | Lý do |
|---|---|---|
| WF001 | Verify Signature | channel signing key |
| WF002 | Notify Sales (Slack) | Slack credential + SALES_SLACK_CHANNEL |
| WF050 | Send Report (Email) | SMTP credential + REPORT_*_EMAIL |

## Acceptance criteria (Definition of Done — scope B)
- [x] PRD-003 đầy đủ (11 mục) + TechSpec chi tiết
- [x] 3 workflow JSON importable; node cần secret = disabled; credential = placeholder
- [x] `.env.example` liệt kê mọi biến
- [x] Sequence + data-flow (Architecture) · error/retry/logging/rollback (runbook)
- [x] Naming convention + folder structure + ADR-0002
- [x] Validator 7 test PASS
- [x] Không secret literal trong repo

## Lệnh chạy lại
```bash
cd workflows && python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Ngoài scope B (go-live)
Gắn `N8N_BASE_URL`+`CRM_BASE`+credential → bật node disabled → thêm endpoint
`GET /dashboard/kpi` cho CRM Core (gap) → theo runbook §Go-live.
