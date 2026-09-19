# n8n Activation Checklist — WF001/WF002/WF003/WF050 (PRD-011 E)

> **Chỉ bật khi env hợp lệ.** Tiền đề: `deploy/secrets/validate-env.sh` = PASS
> (`AUTH_SECRET`, `CRM_BASE`, `N8N_BASE_URL`).

## Gate trước khi bật
- [ ] `set -a; . deploy/.env; set +a; deploy/secrets/validate-env.sh` → **PASS**
- [ ] `GET {CRM_BASE}/dashboard/kpi` → 200 (CR-001)
- [ ] `runtime-health /health/gateway` → `status: ready` (CRM + n8n reachable)

## Theo workflow (registry: `workflows/runtime/registry.py`)
| WF | Điều kiện bật | Credential cần |
|---|---|---|
| WF001 Lead Ingestion | CRM_BASE ok | channel signing (node Verify Signature) |
| WF002 Auto-Tag & Routing | CRM_BASE ok | Slack (node Notify) + SALES_SLACK_CHANNEL |
| WF003 Content Publish | content-factory + publish creds | YouTube/TikTok/FB/Telegram |
| WF050 KPI Sync | GET /dashboard/kpi ok | SMTP (node Send Report) + REPORT_*_EMAIL |

## Trình tự (từng WF một)
1. Import JSON (`deploy/n8n/enable-production.md`).
2. Gắn credential → **bật node disabled**.
3. Verify (`deploy/n8n/verify.md`).
4. Activate. Lỗi → `deploy/n8n/rollback.md`.

> WF003 là planned (registry) — chỉ bật sau khi content-factory + publish connectors có credential.
