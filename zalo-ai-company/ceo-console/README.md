# OMI CEO Console (ZP-001)

CEO Console mobile-first (PWA) + Command API, reuse toàn bộ Company OS. Không dùng API Zalo không chính thức.

- `pwa/` — PWA (index.html mobile-first, manifest, service worker offline shell).
- `src/console_api.py` — Command API: /status /report /build /fix /deploy /health (dry-run plan; auth X-Console-Token).
- `src/health_monitor.py` — VPS/Docker/n8n compat (live docker probe cần shell VPS — PR-002).
- `nginx-console.conf.snippet` — snippet phục vụ /ceo/ + proxy API (kích hoạt khi deploy, không sửa omi.conf).

## Chạy (VPS)
`python3 zalo-ai-company/ceo-console/src/console_api.py` (hoặc thêm service `ceo-console` vào compose) → include snippet nginx → mở `https://<domain>/ceo/`.
Đặt `CONSOLE_TOKEN` để bảo vệ lệnh build/fix/deploy.
