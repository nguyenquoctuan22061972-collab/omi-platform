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

## AFFOS Postgres (staging — Option A; secrets filled from the secret store, never committed)
| Biến | Mô tả | Secret? |
|---|---|---|
| `AFFOS_PG_DB` | DB name (e.g. `affos_staging`) | non-secret |
| `AFFOS_PG_SUPERUSER` | bootstrap superuser (runs `roles.sql` ONCE; not used at runtime) | non-secret |
| `AFFOS_PG_SUPERUSER_PASSWORD` | bootstrap superuser password | **secret** |
| `AFFOS_PG_OWNER_PASSWORD` | `affos_owner` (runs migrations 0001–0005; DDL) | **secret** |
| `AFFOS_PG_SERVICE_PASSWORD` | `affos_service` (runtime least-privilege DML) | **secret** |
| `DATABASE_URL` | derived in compose as `affos_service` — runtime durable store | **secret** (derived) |
| `AFFOS_DB_CONNECT_ATTEMPTS` / `AFFOS_DB_CONNECT_BACKOFF_MS` | connect retry tuning (default 1 / 0) | non-secret |

## COST-1 provider adapters (paid baseline — DRY-RUN by default; keys only when going LIVE under approval)
| Biến | Provider / stage | Bật khi |
|---|---|---|
| `AFFOS_PROVIDERS_LIVE` | master live switch (`=1` enables paid calls) | **OFF** until CEO "execute baseline" |
| `AFFOS_MODEL_API_KEY` | LLM → script | **secret**, only when `AFFOS_PROVIDERS_LIVE=1` |
| `AFFOS_CANVA_API_KEY` | Canva → thumbnail | **secret**, only when live |
| `AFFOS_ELEVENLABS_API_KEY` | ElevenLabs → video/voice | **secret**, only when live |
| `AFFOS_VIDIQ_API_KEY` | vidIQ → publish/metadata | **secret**, only when live |

> COST-1 providers are **refused** unless `AFFOS_PROVIDERS_LIVE=1` **and** the stage's key is present **and**
> an adapter is wired **and** its `ProviderSpec` endpoint is configured — so a missing/zeroed key cannot spend.

## Nguyên tắc
- Không commit secret; repo chỉ có `.env.example` + manifest này.
- Adapter mặc định **tắt** (dry-run) tới khi `<PREFIX>_ENABLED=true` và đủ biến.
- Kiểm tra: `deploy/secrets/validate-env.sh` (in thiếu/đủ, không in giá trị).

## Alert Engine (PRD-012 E) — bật khi cần, dry-run tới khi có credential
| Biến | Bật khi |
|---|---|
| `TELEGRAM_ALERT_ENABLED` | =true để bật alert Telegram |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | khi TELEGRAM_ALERT_ENABLED=true |
| `SMTP_ALERT_ENABLED` | =true để bật alert email |
| `SMTP_HOST`,`SMTP_PORT`,`SMTP_USER`,`SMTP_PASS`,`ALERT_TO_EMAIL` | khi SMTP_ALERT_ENABLED=true |

> Đặt trong `deploy/.env` trên VPS (gitignored). Không commit giá trị.
