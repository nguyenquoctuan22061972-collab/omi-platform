# AFFOS Staging Plan (Milestone 2, TASK 5) — PLAN ONLY, no infra created, no cost incurred

A production-independent staging environment to run the **DRY-RUN** validation (no paid provider calls,
no live affiliate path). Nothing here provisions anything or picks a vendor — it is the plan an operator
executes **after CEO approval**.

## 1. Minimum requirements
| Component | Minimum | Notes |
|---|---|---|
| VPS | 2 vCPU / 4 GB RAM / 40 GB SSD, Linux | runs Docker Compose (postgres + auth-rbac + affos-runtime) |
| Docker Engine + Compose v2 | recent stable | `docker compose` (not the legacy `docker-compose`) |
| PostgreSQL | **16** (via `postgres:16-alpine` in compose) | dedicated instance, **separate from production** |
| Network egress | none required for dry-run | no paid APIs; AWIN/Impact OFF |

## 2. Network & volume layout
```
          VPS (staging host)  ── docker network: omi-staging (bridge, internal) ──
          ┌───────────────────────────────────────────────────────────────────┐
          │  postgres:16-alpine     auth-rbac:8081        affos-runtime:8099    │
          │  (NO host port)       ◄── DATABASE_URL ──────  (affos_service)       │
          │                                               host loopback only     │
          │        ▲  volume ./staging-data/pg            volume ./staging-data/affos
          │        └── migrations run as affos_owner (operator, one-off)        │
          └───────────────────────────────────────────────────────────────────┘
   Reverse proxy / LB (optional)  ──► affos-runtime: liveness /health, readiness /ready
   n8n (separate deployment)      ──► attach to omi-staging to reach affos-runtime:8099 (no DB cred)
```
- **Postgres and auth-rbac are never published to the host/public.** The runtime API binds only to
  `127.0.0.1:8099` on the host for local smoke tests; it is not bound to a public interface.
- Volumes `./staging-data/{pg,auth,affos}` hold staging data, independent of prod volumes.

## 3. Environment variables (names only — fill from the secret store; never commit)
From `deploy/.env.staging.example`: `AUTH_SECRET`, `AFFOS_JWT_ISS`, `AFFOS_JWT_AUD`, `AFFOS_PG_DB`,
`AFFOS_PG_SUPERUSER`, `AFFOS_PG_SUPERUSER_PASSWORD`, `AFFOS_PG_OWNER_PASSWORD`, `AFFOS_PG_SERVICE_PASSWORD`
(+ `AFFOS_SVC_PASSWORD` for n8n WF060). Derived in compose: `DATABASE_URL` (as `affos_service`).
Optional runtime tuning: `AFFOS_DB_CONNECT_ATTEMPTS` (e.g. 5), `AFFOS_DB_CONNECT_BACKOFF_MS` (e.g. 500).
COST-1 provider keys (`AFFOS_*_API_KEY`, `AFFOS_PROVIDERS_LIVE`) are **NOT set in Milestone 2** (dry-run).

## 4. Procedures (each already scripted in the repo)
- **Bring-up:** `docker compose -f deploy/docker-compose.staging.yml --env-file deploy/.env.staging up -d --build`.
- **Backup/restore:** `RUNBOOK` steps 1–2 (`pg_dump --format=custom` off-box; restore-test into a scratch DB via `deploy/scripts/pg_restore.sh`, which refuses prod-looking targets).
- **Apply migrations:** `RUNBOOK` steps 4–5 — bootstrap `roles.sql` once (superuser), then 0001→0005 as `affos_owner`, `ON_ERROR_STOP`.
- **Verify:** `deploy/staging/verify_db.py` + `deploy/staging/verify_http.sh` (PASS/FAIL per check).
- **Smoke (dry-run):** `/health` 200 · `/ready` 200 · unauth ingest 401 · dry-run ingest `stopped`/NOT VERIFIED · `impact` 403.
- **Rollback:** `RUNBOOK` step 8 — 0005 is `REVOKE`+`DROP POLICY` (additive, no data change); full rollback = restore the step-1 backup (already proven loadable by the step-2 restore test).

## 5. Monthly cost estimate (indicative — NOT a quote, no vendor chosen, nothing purchased)
| Option | Assumption | Indicative monthly |
|---|---|---|
| A. Self-managed VPS (Postgres in compose) | 1× small VPS (2 vCPU/4 GB) | **~$12–30/mo** (one VPS; no managed DB fee) |
| B. VPS + managed PostgreSQL 16 | small VPS + smallest managed PG | **~$30–75/mo** (adds managed-DB fee; less ops) |
| AI / provider cost (Milestone 2) | dry-run only, `AFFOS_PROVIDERS_LIVE` OFF | **$0** |
- Assumptions: single-region, smallest tier that runs 3 small containers; backups to the same provider's
  object storage are a few $/mo extra. Figures are **rough industry ranges for sizing discussion only** —
  the operator confirms real prices with the chosen provider before anything is bought.
- **Recommendation:** Option A for Milestone-2 dry-run validation (cheapest, fully isolated); revisit a
  managed DB (Option B) only if prod later needs managed backups/HA.

## 6. Approvals required (each is a separate CEO/operator decision — none taken here)
1. **Approve provisioning** a staging VPS + dedicated PG16, pick the provider/region, name the operator.
2. Operator populates `.env.staging` from the secret store (superuser/owner/service passwords, AUTH_SECRET).
3. Operator runs backup → restore-test → `roles.sql` → migrations 0001–0005 → `verify_db.py` (record gates).
4. Bring up the stack; run `verify_http.sh` + dry-run smoke; record results.
5. (Separate, later) merge PR #11; and only then, the paid baseline (`AFFOS_PROVIDERS_LIVE=1` + explicit "execute baseline").

**Out of scope / still OFF:** any paid call, AWIN live, Impact production, and PR merges — all require their own CEO approval.
