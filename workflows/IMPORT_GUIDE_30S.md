# WF004 — Import trong 30 giây (trên điện thoại)

**File cần:** `WF004.n8n.json` (đính kèm — bấm tải về máy/điện thoại).

## 3 bước
1. **Mở n8n** → menu **☰** → **Workflows** → nút **+** (hoặc ⋮) → **Import from File**.
2. **Chọn `WF004.n8n.json`** vừa tải. Workflow "WF004 — AI Call Intelligence" hiện ra với 8 node
   (Webhook → Validation → Vertex STT → AI Summary → CRM Update → Telegram Notify → Audit → Metrics).
3. **Save**. Xong phần import ✅

> 3 node có ổ khoá (Vertex STT, AI Summary, Telegram) đang **tắt** — bật sau khi gắn credential
> trong n8n. Chưa cần làm ngay để import thành công.

## Bật chạy thật (làm sau, cần credential — ngoài repo)
- Gắn credential Google (STT/Summary) + Telegram → bật 3 node tắt.
- Đặt biến trong `deploy/.env`: `CRM_BASE`, `VERTEX_STT_URL`, `VERTEX_SUMMARY_URL`, `TELEGRAM_CHAT_ID`.
- **Activate** → lấy webhook URL: `POST /webhook/wf004-call-intelligence`.

Không cần copy/paste JSON. Không dán token vào chat.
