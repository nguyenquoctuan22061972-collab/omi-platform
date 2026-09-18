# Env Mapping — OMI Platform (PRD-007 A)

Ánh xạ biến env → nơi tiêu thụ. Giúp biết đặt biến ở đâu.

| Biến | Tiêu thụ bởi | Vị trí đọc |
|---|---|---|
| `AUTH_SECRET` | auth-rbac (JWT) | `apps/auth-rbac` (env), compose `auth-rbac` |
| `CRM_BASE` | dashboard, workflows n8n, adapters test | `config.js`, WF `{{$env.CRM_BASE}}` |
| `N8N_BASE_URL` | vận hành n8n | hạ tầng n8n |
| `TELEGRAM_*` | `libs/integrations/telegram` | env container/n8n |
| `SMTP_*` | `libs/integrations/gmail_smtp`, WF050 email | env |
| `ZALO_OA_*` | `libs/integrations/zalo_oa` | env |
| `FB_PAGE_*` | `libs/integrations/facebook_messenger` | env |
| `OPENAI_*` | `libs/integrations/openai` | env |
| `GCP_*`, `VERTEX_*` | `libs/integrations/vertex_ai` | env (+ ADC runtime) |
| `<PREFIX>_ENABLED` | activation layer (`libs/integrations/activation.py`) | env |

## Thứ tự nạp
1. `deploy/.env` (từ `.env.example` + `secrets-manifest.md`).
2. Compose truyền vào container qua `environment:`.
3. Adapter đọc từ process env; enable flag quyết định bật/tắt.

## Kiểm tra
`set -a; . deploy/.env; set +a; deploy/secrets/validate-env.sh`
