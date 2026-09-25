# ZALO AI COMPANY v1.0 — Command Center

Chế độ Orchestrator: **CTO = ChatGPT · Builder = Claude**. Nguyên tắc: Analyze → Build → QA → PASS,
additive-only, không sửa từng node, secret env-only.

## 9 phòng ban (map vào module đã build — reuse, không tạo trùng)
| Dept | Stack | Runtime binding | Status | Quyền |
|---|---|---|---|---|
| Engineering | n8n/VPS/Docker | `orchestrator/runtime` | 🔴 blocked | P0 |
| Zalo Platform | Zalo OA API | `libs/integrations/zalo_oa.py` | 🔴 blocked | P0 |
| CRM | Supabase | `apps/crm-core` | 🟠 degraded | P1 |
| Company Vault | Google Drive + RAG | `libs/prompts` | 🔴 blocked | P1 |
| Sales | lead engine | `libs/lead/engine.py` | 🟢 active | — |
| Content Factory | AI/n8n/publish | `apps/content-factory` | 🟢 active | — |
| Security | audit/rbac | `libs/audit` | 🟢 active | — |
| QA | unittest/CI | `.github/workflows/ci.yml` | 🟢 active | — |
| Monitoring | metrics/alerts/health | `apps/runtime-health` | 🟢 active | P2 |

## Điều khiển
- `src/command_center.py` — load + validate manifest, readiness, gom permission requests.
- `company.manifest.json` — nguồn sự thật (9 dept + permission register).
- Readiness: `PYTHONPATH=src python3 -c "from command_center import CommandCenter,json; ..."`

## Trạng thái v1.0
5 active · 1 degraded · 3 blocked. Blocked/degraded đều do **quyền/hạ tầng ngoài** → xem `PERMISSION_REQUESTS.md`.
