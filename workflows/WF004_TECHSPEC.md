# WF004 — AI Call Intelligence · TechSpec (WO-015)

> **Additive.** Không đụng PRD001–010 / ADR / capability-map / naming. Secret env-only.
> File workflow: `workflows/WF004.n8n.json` (import vào n8n). Không nối credential trong repo.

## 1. Mục tiêu
Nhận file ghi âm cuộc gọi → chuyển giọng nói thành văn bản (STT) → tóm tắt bằng AI →
ghi vào CRM → thông báo Telegram → ghi audit → phát metric.

## 2. Luồng (pipeline)
```
Webhook → Validation → Vertex STT → AI Summary → CRM Update → Telegram Notify → Audit → Metrics
```

## 3. Node & vai trò
| Node | Type | Enabled | Ghi chú |
|---|---|---|---|
| Webhook | webhook | ✅ | POST `/webhook/wf004-call-intelligence` |
| Validation | function | ✅ | bắt buộc `audio_url` + `contact.phone/email`; không log secret |
| Vertex STT | httpRequest | ⛔ disabled | credential `googleApi` (đặt trong n8n); URL `$env.VERTEX_STT_URL` |
| AI Summary | httpRequest | ⛔ disabled | credential `googleApi`; URL `$env.VERTEX_SUMMARY_URL` |
| CRM Update | httpRequest | ✅ | `$env.CRM_BASE/conversations` (nội bộ, không credential ngoài) |
| Telegram Notify | telegram | ⛔ disabled | credential `telegramApi`; `$env.TELEGRAM_CHAT_ID` |
| Audit | httpRequest | ✅ | `$env.CRM_BASE/audit` — event `workflow_activation` |
| Metrics | httpRequest | ✅ | `$env.CRM_BASE/metrics/ingest` — `workflow_count` |

## 4. Cấu hình (v2 — KHÔNG dùng $env)
n8n chặn `$env` trong expression, nên base URL nằm ở node **Config** (Set), downstream tham chiếu
`$('Config').item.json.<key>`:
| Key (Config) | Dùng cho | Secret? |
|---|---|---|
| `crm_base` | CRM Update / Audit / Metrics | không (DNS nội bộ) |
| `vertex_stt_url` | Vertex STT | không |
| `vertex_summary_url` | AI Summary | không |
| `telegram_chat_id` | Telegram Notify | không |
| Credential `googleApi`, `telegramApi` | gắn trong n8n UI (token KHÔNG nằm trong JSON) | có → credential |

> Thay thế: đặt `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (VPS, restart n8n) nếu muốn quay lại `$env`.

## 5. Nguyên tắc an toàn
- Không secret literal trong JSON (kiểm bằng `workflows/tests/test_wf004.py`).
- Node cần secret (STT/Summary/Telegram) **disabled** tới khi gắn credential.
- URL lấy từ node Config — không hardcode trong từng httpRequest.

## 6. Tích hợp hệ thống hiện có (reuse, không fork)
- CRM: endpoint conversations của `apps/crm-core` (PRD-001).
- Audit: vocab `libs/audit` (`workflow_activation`).
- Metrics: khớp `libs/metrics` (`workflow_count`).
