# Tech Spec — Automation n8n (DRAFT)

**Tên Module:** Automation n8n
**PRD tham chiếu:** [`../PRD/PRD-003.md`](../PRD/PRD-003.md) (DRAFT)

> Scope B: workflow JSON **import được**, chưa nối credential/deploy. Node để trạng
> thái enabled nhưng credential trống → người dùng gắn trong n8n UI.

## Kiến trúc
n8n gọi CRM Core REST API (PRD-001 §6) qua HTTP Request node. Base URL = biến môi
trường n8n `CRM_BASE`. 3 workflow độc lập, kích hoạt bằng Webhook/Schedule.

```
WF001  Webhook(crm/lead) → Normalize(Code) → HTTP POST /contacts → HTTP POST /messages → Respond
WF002  Webhook(crm/new-conversation) → SuggestTags(Code) → HTTP POST /contacts(update tags) → Switch(route) → NoOp(assign)
WF050  Schedule(cron) → HTTP GET /dashboard/kpi* → Format(Code) → NoOp(publish)
       (*endpoint KPI chưa có ở CRM Core — xem PRD-003 §11 Gap)
```

## Chuẩn file
- Vị trí: `workflows/<WF>/workflow.json` — định dạng export n8n (name, nodes,
  connections). Import: n8n UI → Import from File.
- README mỗi WF nêu trigger, mapping PRD, credential cần gắn.

## Node & tham số chính
| WF | Node | Type | Ghi chú |
|---|---|---|---|
| WF001 | Webhook | webhook | POST `crm/lead` |
| WF001 | Normalize | code | payload → {name,phone,email,channel,message} |
| WF001 | Create Contact | httpRequest | POST `={{$env.CRM_BASE}}/contacts` |
| WF001 | Add Message | httpRequest | POST `={{$env.CRM_BASE}}/messages` |
| WF001 | Respond | respondToWebhook | 200 |
| WF002 | Trigger | webhook | POST `crm/new-conversation` |
| WF002 | Suggest Tags | code | mirror `tagging.py` rule-based |
| WF002 | Update Tags | httpRequest | POST `/contacts` (merge tags) |
| WF002 | Route | switch | theo tag/stage |
| WF002 | Assign | noOp | điểm cắm notify Sales |
| WF050 | Schedule | scheduleTrigger | cron |
| WF050 | Read KPI | httpRequest | GET `/dashboard/kpi` (gap) |
| WF050 | Format | code | format số liệu |
| WF050 | Publish | noOp | điểm cắm gửi báo cáo |

## Bảo mật
Không commit credential/token. Chỉ dùng `{{$env.CRM_BASE}}` và credential do n8n quản.

## QA (scope B)
Validator `workflows/tests/test_workflows.py`: JSON hợp lệ · có trigger + HTTP node ·
connection trỏ node tồn tại · URL HTTP dùng `$env.CRM_BASE` (không hardcode host/secret).

## Đường nâng cấp (ngoài scope B — cần credential/n8n)
Gắn credential từng kênh → bật node → deploy vào n8n → thêm retry/backoff +
idempotency. Bổ sung KPI endpoint cho CRM Core trước khi bật WF050.
