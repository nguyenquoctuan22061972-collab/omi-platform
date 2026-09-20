# WF004 — PRODUCTION CHECKLIST (10 bước)

> Không rebuild. Dùng `workflows/WF004.n8n.json` (v2, 9 node, không $env).

- [ ] **1. Import** `WF004.n8n.json` vào n8n (Import from File). Kỳ vọng 9 node.
- [ ] **2. Config** — mở node `Config`, điền `vertex_stt_url`, `vertex_summary_url`, `telegram_chat_id`; kiểm `crm_base=http://crm-core:8080`.
- [ ] **3. Google credential** — tạo credential `Google API` (service account), gán cho **Vertex STT** và **AI Summary**.
- [ ] **4. Telegram credential** — tạo credential `Telegram API` (bot token), gán cho **Telegram Notify**.
- [ ] **5. Enable** 3 node: Vertex STT, AI Summary, Telegram Notify (bỏ disabled).
- [ ] **6. Network** — xác nhận container n8n cùng docker network với `crm-core` (CRM/Audit/Metrics gọi được `http://crm-core:8080`).
- [ ] **7. Save** workflow.
- [ ] **8. Test webhook** (test URL) bằng `TEST_PAYLOADS.md` → Validation xanh, chuỗi chạy tới Metrics.
- [ ] **9. Activate** workflow → lấy production URL `/webhook/wf004-call-intelligence`.
- [ ] **10. Smoke production** — gửi 1 payload thật; kiểm CRM có conversation (channel=call), Telegram nhận summary, Audit + Metrics ghi nhận.

**Định nghĩa Done:** cả 10 mục ✅, workflow Active, 3 node enabled, không lỗi execution.
