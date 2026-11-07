# WF060 — AFFOS Affiliate Revenue Ingest (dry-run)

**Additive.** Does not touch WF001–WF050 or crm-core. Pairs with the AFFOS Revenue Ingestion API
(`AFFOS/runtime/revenue_api.py`, wired into `AFFOS/runtime/server.py`).

## Flow
```
Schedule (hourly) → Config → Login (service acct) → Ingest → Verify/Report → Reconcile → If Alert → (Slack/email sink)
```

## Endpoints called
| Node | Method | URL | Auth |
|---|---|---|---|
| Login | POST | `{auth_base}/auth/login` | service account (credential in n8n UI) |
| Ingest | POST | `{ingest_base}/affos/revenue/ingest` | `Authorization: Bearer <JWT>` + `Idempotency-Key` |
| Verify/Report | GET | `{ingest_base}/affos/revenue/report?provider=&start=&end=` | Bearer |

Defaults: `ingest_base=http://affos-runtime:8099`, `auth_base=http://auth-rbac:8081`,
`provider=awin`, `mode=dry-run`, window = last 24h.

## Safety (S1–S4 scope)
- `workflow.active=false`; **Login / Ingest / Verify nodes are `disabled`** until a service-account
  credential + CTO approval exist. Nothing fires on import.
- Body sends `approved:false` and `mode:dry-run` → the API can only STOP/dry-run; **no live affiliate
  call** is possible from this workflow (no production transport is wired).
- **Impact is OFF**: the API rejects `provider:impact` with 403 until re-approved by the CTO.
- No secret is stored in this JSON — the service-account credential lives in the n8n credential store.

## Going live (later sprint, needs CTO approval)
1. Create the `svc-revenue` user (role granting `revenue:ingest`) and an n8n credential for it.
2. Enable the disabled nodes.
3. Set `mode=live` and `approved=true` ONLY after AWIN creds + egress are approved (real-money / cost).
4. Keep Impact OFF until separately approved.
