# WF002 — AI Auto-Tag & Sales Routing (n8n) · PLACEHOLDER

**Trạng thái:** 🟡 Placeholder — chưa nối credential/deploy.
**Map PRD-001 §9:** bước 3 (AI gắn tag) + bước 4 (Sales xử lý).

## Luồng n8n (dự kiến)
```
[Trigger: sau WF001 / new conversation]
   → [AI node hoặc Function: suggest tags]   (điểm cắm AI thật; MVP dùng rule-based)
   → [HTTP Request: cập nhật tags contact]
   → [Switch theo tag/stage → phân công Sales]
   → [Notify: Slack/Email cho Sales]
```

## Ghi chú
- Logic tag tham chiếu `apps/crm-core/src/crm/tagging.py` (rule-based stub).
- Phân quyền/định tuyến Sales cần RBAC (Risk §11) → giai đoạn sau.

Xem `workflow.json` (skeleton placeholder).
