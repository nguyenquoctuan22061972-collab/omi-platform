# Secrets Manifest — OMI Platform (PRD-007 A)

> Danh mục secret/biến. **Không chứa giá trị thật.** Giá trị đặt trong `deploy/.env`
> (gitignored) hoặc secret manager. Xoay theo `docs/Operations/credential-rotation.md`.

## Core (bắt buộc)
| Biến | Mô tả | Nguồn |
|---|---|---|
| `AUTH_SECRET` | Ký JWT (≥32 bytes) | `openssl rand -hex 32` |
| `CRM_BASE` | URL CRM Core (vd `/api/crm` hoặc http://crm-core:8080) | nội bộ |
| `N8N_BASE_URL` | URL n8n | hạ tầng n8n |

## Adapter (bắt buộc khi bật `<PREFIX>_ENABLED=true`)
| Adapter | Enable flag | Biến |
|---|---|---|
| Telegram | `TELEGRAM_ENABLED` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| SMTP (Gmail) | `SMTP_ENABLED` | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` |
| Zalo OA | `ZALO_OA_ENABLED` | `ZALO_OA_ID`, `ZALO_OA_ACCESS_TOKEN` |
| Facebook | `FB_PAGE_ENABLED` | `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN` |
| OpenAI | `OPENAI_ENABLED` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| Vertex AI | `VERTEX_ENABLED` | `GCP_PROJECT`, `GCP_LOCATION`, `VERTEX_MODEL` |

## Nguyên tắc
- Không commit secret; repo chỉ có `.env.example` + manifest này.
- Adapter mặc định **tắt** (dry-run) tới khi `<PREFIX>_ENABLED=true` và đủ biến.
- Kiểm tra: `deploy/secrets/validate-env.sh` (in thiếu/đủ, không in giá trị).
