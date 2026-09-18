# Tech Spec — Automation n8n

**Tên Module:** Automation n8n
**PRD tham chiếu:** [`../PRD/PRD-003.md`](../PRD/PRD-003.md) (DRAFT)
**Liên quan:** [`Architecture/Automation-n8n-flows.md`](../Architecture/Automation-n8n-flows.md) ·
[`Operations/Automation-n8n-runbook.md`](../Operations/Automation-n8n-runbook.md) ·
[`CTO-Bible/adr/ADR-0002-automation-n8n.md`](../CTO-Bible/adr/ADR-0002-automation-n8n.md)

## 1. Kiến trúc
n8n điều phối (orchestrate) CRM Core REST API (PRD-001 §6). 3 workflow độc lập; state
nằm ở CRM Core. Cấu hình runtime qua biến môi trường (`.env.example`).

## 2. Thành phần & node (map module)
| WF | Node | Type | Enabled | Ghi chú |
|---|---|---|:--:|---|
| WF001 | Webhook | webhook | ✅ | POST `crm/lead` |
| WF001 | Verify Signature | code | ⛔ disabled | cần channel signing secret |
| WF001 | Normalize | code | ✅ | payload → chuẩn |
| WF001 | Create Contact | httpRequest | ✅ | POST `{{$env.CRM_BASE}}/contacts` |
| WF001 | Add Message | httpRequest | ✅ | POST `{{$env.CRM_BASE}}/messages` |
| WF001 | Respond | respondToWebhook | ✅ | 200 |
| WF002 | Trigger | webhook | ✅ | POST `crm/new-conversation` |
| WF002 | Suggest Tags | code | ✅ | mirror `tagging.py` |
| WF002 | Update Tags | httpRequest | ✅ | POST `/contacts` (merge) |
| WF002 | Route | switch | ✅ | theo tag |
| WF002 | Notify Sales (Slack) | slack | ⛔ disabled | cần Slack credential |
| WF050 | Schedule | scheduleTrigger | ✅ | cron |
| WF050 | Read KPI | httpRequest | ✅ | GET `/dashboard/kpi` (gap §11) |
| WF050 | Format | code | ✅ | format số liệu |
| WF050 | Send Report (Email) | emailSend | ⛔ disabled | cần SMTP credential |

> Quy tắc: **mọi node cần secret → `disabled`** để import không lỗi; Admin bật sau khi
> gắn credential. HTTP node tới CRM chỉ dùng `{{$env.CRM_BASE}}` (không secret).

## 3. Sequence & Data-flow
Xem `Architecture/Automation-n8n-flows.md` (sequence diagram + data-flow chi tiết).

## 4. Error handling (tóm tắt — chi tiết trong runbook)
- HTTP node bật `Continue On Fail` + kiểm tra status; lỗi 4xx → nhánh xử lý lỗi
  (không retry mù); 5xx/timeout → retry.
- Webhook luôn `Respond` sớm để tránh timeout kênh gửi.

## 5. Retry
- HTTP node: `maxTries=3`, backoff luỹ thừa (n8n retryOnFail + waitBetweenTries),
  chi tiết runbook §Retry.
- Idempotency: dùng `phone|email` (CRM merge) → retry an toàn, không nhân đôi contact.

## 6. Logging
- Dựa vào n8n Execution log (mỗi run có input/output/timestamp).
- Sự kiện nghiệp vụ (tag, route) đẩy về CRM `audit_logs` (PRD-002) khi tích hợp.
- Không log secret/PII thô ra ngoài execution store.

## 7. Rollback
- Workflow versioned trong Git (`workflows/*/workflow.json`).
- Rollback = re-import phiên bản Git trước + tắt workflow lỗi. Chi tiết runbook §Rollback.

## 8. Cấu hình
`.env.example` (`workflows/.env.example`): `N8N_BASE_URL`, `CRM_BASE`, credential kênh.

## 9. Naming & folder
Theo `CTO-Bible/naming-and-structure.md`.

## 10. QA / Acceptance
`workflows/tests/test_workflows.py` (validator tĩnh) + `docs/QA/Automation-n8n-checklist.md`
(test cases TC1-TC7 + acceptance criteria).

## 11. Gap
CRM Core cần expose `GET /dashboard/kpi` (PRD-001 §6 chỉ 5 endpoint). WF050 để sẵn node
nhưng chỉ chạy đúng sau khi có endpoint.
