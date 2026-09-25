# ZALO AI COMPANY — PERMISSION REQUESTS

> Việc Builder KHÔNG tự làm được vì cần credential/hạ tầng ngoài repo. Cấp theo ưu tiên.

## P0 — chặn go-live, cần ngay
- **PR-001 · Zalo Platform** — Zalo OA `id` + `access_token` (đặt trong `deploy/.env`, không commit). Mở khoá mọi tác vụ Zalo.
- **PR-002 · Engineering** — Kênh thực thi VPS/n8n từ session. Hiện **egress bị chặn 403** tới `ycdtuo.ezn8n.com`; và không có shell VPS. Cần: (a) mở allowlist egress tới domain n8n, hoặc (b) chạy Claude Code trực tiếp trên VPS. Mở khoá auto-deploy + gọi n8n.

## P1 — cần để hoàn thiện kiến trúc
- **PR-003 · CRM** — Supabase `PROJECT_URL` + `service_role key`. Hiện CRM chạy SQLite (degraded). Mở khoá CRM trên Supabase.
- **PR-004 · Company Vault** — Google Drive OAuth + vector store cho RAG. Mở khoá Company Vault.

## P2 — nâng cấp, không chặn
- **PR-005 · Monitoring** — Telegram bot token / SMTP creds để alert live (đang dry-run).

## Cách cấp an toàn
- Secret đặt trong `deploy/.env` trên VPS (gitignored) hoặc credential store của n8n/Supabase. **Không dán token vào chat/commit.**
- Sau khi cấp, cập nhật `status` phòng ban tương ứng trong `company.manifest.json` (active).
