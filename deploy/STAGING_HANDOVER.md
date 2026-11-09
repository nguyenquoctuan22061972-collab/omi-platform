# AFFOS Staging Handover Package (Milestone 2)

Everything an operator needs to stand up and verify AFFOS staging **without guessing**. DRY-RUN only: no
paid provider call, no live affiliate path. Run the steps in order; record each gate's result in §11.

> Repository-side hardening is complete and verified offline/on scratch. Milestone 2 is **not** PASS until
> these steps are executed on a **real, production-independent staging host** and the evidence recorded.

## 1. Infrastructure prerequisites
- 1× VPS (min 2 vCPU / 4 GB / 40 GB SSD), Linux, **separate from production**.
- Docker Engine + Compose v2; **PostgreSQL 16** (via `postgres:16-alpine` in the compose).
- No inbound ports for Postgres (compose publishes none). Outbound egress not needed for dry-run.
- Full sizing + indicative cost ranges: `deploy/STAGING_PLAN.md`.

## 2. Environment variables
Copy `deploy/.env.staging.example` → `deploy/.env.staging` and fill from the secret store. Non-secret:
`AFFOS_PG_DB`, `AFFOS_PG_SUPERUSER`, `AFFOS_JWT_ISS`, `AFFOS_JWT_AUD`. Runtime tuning (optional):
`AFFOS_DB_CONNECT_ATTEMPTS` (e.g. 5), `AFFOS_DB_CONNECT_BACKOFF_MS` (e.g. 500). COST-1 provider keys
(`AFFOS_*_API_KEY`, `AFFOS_PROVIDERS_LIVE`) are **NOT set in Milestone 2**.

## 3. Secrets checklist (from the secret store — never commit, never echo)
- [ ] `AUTH_SECRET` (`openssl rand -hex 32`; shared by auth-rbac + affos-runtime)
- [ ] `AFFOS_PG_SUPERUSER_PASSWORD` (bootstrap superuser; runs `roles.sql` once)
- [ ] `AFFOS_PG_OWNER_PASSWORD` (`affos_owner`; migrations/DDL)
- [ ] `AFFOS_PG_SERVICE_PASSWORD` (`affos_service`; runtime least-privilege DML)
- [ ] (WF060 only) `AFFOS_SVC_PASSWORD` for n8n's API login — **not** a DB credential.
Verify presence without printing values: `deploy/secrets/validate-env.sh`.

## 4. Backup / restore procedure
- Pre-migration backup + restore-TEST: `deploy/RUNBOOK_apply_0001_0005.md` steps 1–2 (`pg_dump
  --format=custom`; restore into a scratch DB via `deploy/scripts/pg_restore.sh`, which refuses
  prod-looking targets, allows only scratch/staging, `--single-transaction`, no `--clean`).
- **Rehearsed end-to-end on scratch PG16** (`deploy/staging/backup_restore_rehearsal.sh` → 13/13 PASS):
  dump → sha256 → restore → verify schema/indexes/RLS/row-counts (no data loss) → re-establish grants.
- **Recovery note (important):** `pg_restore.sh` uses `--no-owner --no-privileges`, so the restored DB has
  the schema + data but **not** the GRANTs/ownership. A full recovery re-applies `deploy/postgres/roles.sql`
  **as the superuser** (objects are owned by the restoring superuser) then `0005` to re-grant the runtime
  role; the rehearsal script does exactly this.

## 5. Migration procedure
`deploy/RUNBOOK_apply_0001_0005.md` steps 4–6: bootstrap `roles.sql` once (superuser) → apply
`0001→0005` as `affos_owner` with `ON_ERROR_STOP` → verify (23 tables / 28 policies / 3 `ux_*_src` /
privilege matrix). Ordering, idempotency, duplicate pre-check and unique-constraint enforcement are
**rehearsed on scratch PG16** (`deploy/staging/migration_safety_rehearsal.sh` → 8/8 PASS).

## 6. Security verification
- Static (no DB, runnable anywhere / in CI): `python deploy/staging/verify_security.py` (10/10) — no public
  PG port, runtime = `affos_service` (not owner/superuser), no n8n DB creds, `roles.sql` least-privilege,
  no committed secret.
- Live (on staging): `python deploy/staging/verify_db.py` — 23 tables, RLS, and the live privilege matrix
  (INSERT `cost.call` ALLOW; UPDATE/DELETE `audit_logs`, INSERT financial, CREATE TABLE → DENY 42501).

## 7. HTTP smoke tests
`BASE_URL=http://localhost:8099 deploy/staging/verify_http.sh`: `/health` 200 (liveness), `/ready` 200
(readiness), unauthenticated ingest → 401 (JWT `iss`/`aud` enforced). Operator negatives (Postgres
stopped): `/ready` → 503, authed ingest → 503 (no false success); restart → reconnect.

## 8. Cost / live-mode verification
Offline guards proven by `AFFOS.tests.test_cost_guards` (live OFF by default; needs switch+credential+
adapter; ceiling refusal is unpriced and skips the provider; AWIN/Impact OFF). On staging confirm
`AFFOS_PROVIDERS_LIVE` is unset and no `AFFOS_*_API_KEY` is present.

## 9. Rollback procedure
`deploy/RUNBOOK_apply_0001_0005.md` step 8: 0005 is `REVOKE` + `DROP POLICY` (additive; no data change);
full rollback = restore the step-1 backup (the step-2 restore test already proved it loads). Services:
`docker compose -f deploy/docker-compose.staging.yml down` (data volumes persist unless removed).

## 10. DB outage & recovery (runbook)
- **Detect:** `/ready` returns **503** (DB unreachable); `/health` stays 200 (process alive). Container is
  NOT restart-looped (healthcheck is liveness). Logs show `StoreUnavailable` (no secret in the message).
- **During outage:** write endpoints return **503 "store unavailable"** — they do **not** fabricate success
  and do **not** downgrade to SQLite. Readiness probing is cheap (one `SELECT 1`), serialized, and
  reconnect is single-flighted (`_STORE_LOCK`) so recovery causes **one** reconnect, not a storm.
- **Recover:** bring Postgres back; within `AFFOS_DB_CONNECT_ATTEMPTS × backoff` the next request/readiness
  probe reconnects automatically and `/ready` returns 200. No process restart required.
- **If the connection string or credentials changed:** update `.env.staging` from the secret store and
  restart `affos-runtime` (`docker compose ... up -d affos-runtime`).

## 11. GO / NO-GO checklist + evidence template
Record each; proceed only on PASS. **ABORT** on any ✗ and restore if a migration had started.

| Gate | Result (PASS/FAIL) | Evidence (command / output / timestamp) |
|---|---|---|
| Staging host provisioned, isolated from prod | | |
| `.env.staging` filled from secret store (no values committed) | | |
| Backup taken + restore-TEST passed (scratch) | | |
| Migrations 0001–0005 applied in order (23 tables) | | |
| `verify_db.py` privilege matrix PASS | | |
| `verify_security.py` PASS | | |
| `verify_http.sh` (health/ready/401) PASS | | |
| DB-down negative: `/ready` 503 + ingest 503 | | |
| `AFFOS_PROVIDERS_LIVE` unset; no provider keys | | |
| Rollback procedure confirmed available | | |

## Responsibility matrix (who does what)
| Action | Builder (Claude) | CTO (review) | CEO (approve) | Operator (staging host) |
|---|---|---|---|---|
| Code + tests + scratch rehearsals + docs | ✅ done | nghiệm thu | — | — |
| Merge PR #11 / #12 | — | recommend | ✅ required | — |
| Provision VPS + PG16 | — | — | ✅ approve | ✅ execute |
| Fill secrets in secret store | — | — | ✅ approve | ✅ execute |
| Backup → restore-test → migrate 0001–0005 | — | — | ✅ approve | ✅ execute |
| Run verify_db / verify_http / verify_security on staging | — | review evidence | — | ✅ execute |
| Enable paid baseline (`AFFOS_PROVIDERS_LIVE=1`) | — | — | ✅ required | ✅ execute |
| AWIN live / Impact production | — | — | ✅ required | ✅ execute |

**Builder cannot and must not:** provision infra, apply migrations on real staging, change secrets, deploy,
call paid APIs, or merge. Those are CEO-approved, operator-executed steps.
