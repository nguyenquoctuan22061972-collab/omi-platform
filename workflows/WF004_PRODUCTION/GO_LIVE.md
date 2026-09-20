# WF004 — GO LIVE

1. Hoàn tất `PRODUCTION_CHECKLIST.md` bước 1–8 (import, Config, credential, enable, network, save, test).
2. **Activate** WF004 trong n8n.
3. Ghi lại **Production webhook URL**: `https://<n8n-domain>/webhook/wf004-call-intelligence`.
4. Smoke production bằng payload #1 (`TEST_PAYLOADS.md`).
5. Xác nhận 3 tín hiệu:
   - CRM: conversation mới (channel=call).
   - Telegram: nhận summary.
   - Audit + Metrics: có record `workflow_activation` / `workflow_count`.
6. Nếu bất kỳ bước nào đỏ → theo `ROLLBACK.md` (Deactivate) rồi báo lại node lỗi.

**Go/No-Go:** Go khi bước 4–5 xanh; No-Go → rollback + fix.
