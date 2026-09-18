# Inbox Domain (PRD-006 Module B)

Unified inbox skeleton, standalone. 4 kênh qua **adapter** interface thống nhất:
Telegram · Email · Zalo · Facebook (placeholder). **Không hardcode credential** — cờ
`configured` đọc từ `window.OMI_CONFIG.CHANNELS` runtime.

- `adapters.js`: interface `{ key, label, configured, fetchMessages }`.
- `inbox.js`: unified list + lọc theo kênh.
- `mock/messages.json`: dữ liệu mẫu.

## Chạy
`http://localhost:8000/inbox/` (sau `python3 -m http.server` trong apps/dashboard).
