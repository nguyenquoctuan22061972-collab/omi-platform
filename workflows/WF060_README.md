# WF060 — AFFOS Affiliate Revenue Ingest (dry-run)

**Additive.** Does not touch WF001–WF050 or crm-core. File: `workflows/WF060.n8n.json`
(top-level `.n8n.json` convention like WF004/WF005 — it uses a `Config` Set node instead of
`$env`, so it is intentionally outside the legacy `WF*/workflow.json` validator).
Pairs with the AFFOS Revenue Ingestion API (`AFFOS/runtime/revenue_api.py`, wired into
`AFFOS/runtime/server.py`).

## Flow
```
Schedule (hourly) → Config → Login (service acct) → Ingest → Verify/Report → Reconcile → If Alert → (Slack/email sink)
```

## Endpoints called
| Node | Method | URL | Auth |
|---|---|---|---|
| Login | POST | `{auth_base}/auth/login` | username from Config + `$vars.AFFOS_SVC_PASSWORD` (n8n variable, not committed) |
| Ingest | POST | `{ingest_base}/affos/revenue/ingest` | `Authorization: Bearer <JWT>` + `Idempotency-Key` |
| Verify/Report | GET | `{ingest_base}/affos/revenue/report?provider=&start=&end=` | Bearer |

Defaults: `ingest_base=http://affos-runtime:8099`, `auth_base=http://auth-rbac:8081`,
`svc_user=svc-revenue`, `provider=awin`, `mode=dry-run`, window = last 24h.

## Safety (S1–S4 scope)
- `active=false`; **Login / Ingest / Verify nodes are `disabled`** until a service-account
  credential + CTO approval exist. Nothing fires on import.
- The ingest body sends `mode:dry-run` and no `approved` flag → the API defaults to not-approved and
  can only STOP/dry-run; **no live affiliate call** is possible (no production transport is wired).
- **Impact is OFF**: the API rejects `provider:impact` with 403 until re-approved by the CTO.
- No secret in this JSON — the service password is an n8n variable (`$vars.AFFOS_SVC_PASSWORD`).

## Going live (later sprint, needs CTO approval)
1. Create the `svc-revenue` user (role granting `revenue:ingest`) + set `AFFOS_SVC_PASSWORD` in n8n.
2. Enable the disabled nodes.
3. Switch to the approval-gated live path (see Phase 3 Design Revision v2) ONLY after AWIN creds +
   egress are approved (real-money / cost).
4. Keep Impact OFF until separately approved.
