# WF005 — Recovery Playbook (PR-005.1)

Sự cố thường gặp & cách xử lý:

- 1. Lỗi gửi Zalo (401/403): kiểm ACCESS_TOKEN credential còn hạn; refresh token OA.
- 2. Webhook 404: WF005 chưa Activate hoặc sai path /webhook/wf005-zalo-inbound.
- 3. CRM node đỏ: n8n không cùng network với crm-core → sửa Config.crm_base.
- 4. Rate-limited: giảm tải hoặc tăng rate_limit_per_min; token-bucket tự hồi.
- 5. Double-message: idempotency (event_id) đã chặn; kiểm Zalo msg_id có gửi kèm.
- 6. Rollback: Deactivate WF005 (không xoá); ghi RollbackLog; điều tra Executions.
