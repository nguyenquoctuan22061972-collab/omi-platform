# n8n — Enable Production (PRD-007 C)

Bật automation thật sau khi có credential. **Không sửa workflow business** (chỉ bật node
đang `disabled` + gắn credential).

## Tiền đề
- `N8N_BASE_URL` + `CRM_BASE` đã đặt (`deploy/secrets/validate-env.sh` PASS).
- CR-001 đã có → WF050 dùng `GET /dashboard/kpi`.

## Bước
1. **Import workflow** (nếu chưa): n8n UI → Import from File → `workflows/WF001|WF002|WF050/workflow.json`.
2. **Gắn credential** (n8n → Credentials), map tới node:
   - WF001 `Verify Signature`: channel signing secret.
   - WF002 `Notify Sales (Slack)`: Slack credential + `SALES_SLACK_CHANNEL`.
   - WF050 `Send Report (Email)`: SMTP credential + `REPORT_*_EMAIL`.
3. **Bật node disabled**: mở từng node → tắt "Disabled".
4. **Đặt biến n8n**: `CRM_BASE` (Settings → Variables/Env).
5. **Activate workflow**: bật Active cho WF001/WF002/WF050.
6. **Verify**: theo `verify.md`.

## Nguyên tắc
- Chỉ bật node/credential; không đổi logic node (giữ nguyên business).
- Bật từng workflow một, verify xong mới bật cái tiếp.
