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

## 4. Biến môi trường (đặt trong n8n / deploy/.env — KHÔNG commit giá trị)
| Biến | Dùng cho |
|---|---|
| `CRM_BASE` | CRM Update / Audit / Metrics |
| `VERTEX_STT_URL` | endpoint Vertex Speech-to-Text |
| `VERTEX_SUMMARY_URL` | endpoint Vertex summary/LLM |
| `TELEGRAM_CHAT_ID` | kênh nhận thông báo |
| Credential `googleApi`, `telegramApi` | gắn trong n8n UI (không nằm trong JSON) |

## 5. Nguyên tắc an toàn
- Mọi URL dùng `$env.*` — không hardcode host.
- Node cần secret (STT/Summary/Telegram) **disabled** tới khi gắn credential trong n8n.
- JSON không chứa secret literal (kiểm bằng `workflows/tests/test_wf004.py`).

## 6. Tích hợp hệ thống hiện có (reuse, không fork)
- CRM: tái dùng endpoint conversations của `apps/crm-core` (PRD-001).
- Audit: cùng vocab `libs/audit` (`workflow_activation`).
- Metrics: khớp `libs/metrics` (`workflow_count`).
