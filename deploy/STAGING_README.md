# AFFOS Revenue — Staging bring-up (PROPOSAL)

Additive staging deployment for PR #4 (S1–S6). Nothing here runs automatically; an operator brings it
up on the staging host after approval. DRY-RUN only; Impact OFF; no live affiliate call is possible.

## Files
- `Dockerfile.affos-runtime` — image for `AFFOS/runtime/server.py` (port 8099).
- `docker-compose.staging.yml` — staging `postgres` + `auth-rbac` + `affos-runtime`.
- `.env.staging.example` — env var NAMES (copy to `.env.staging`, fill from your secret store).

## Bring-up
```bash
cp deploy/.env.staging.example deploy/.env.staging   # then fill AUTH_SECRET, AFFOS_PG_*, etc.
docker compose -f deploy/docker-compose.staging.yml --env-file deploy/.env.staging up -d --build
# 1) Bootstrap roles ONCE (superuser), BEFORE migrations — creates the Supabase-compat roles that
#    0002/0004 need on a vanilla Postgres, plus least-privilege affos_owner (DDL) / affos_service (DML):
#      psql "$SUPERUSER_URL" -f deploy/postgres/roles.sql
#      # then set role passwords out of band (see the bottom of roles.sql).
# 2) Apply migrations as the OWNER role (affos_owner), in order 0001 → 0002 → 0003 → 0004 → 0005
#    (see the apply-0004 runbook: backup → restore test → duplicate pre-check → apply → verify).
#    0005 grants the least-privilege runtime role (affos_service) INSERT/UPDATE on the operational
#    store tables ONLY (ingestion_approvals/idempotency, audit_logs) — no BYPASSRLS, no DDL.
```
The runtime durable store (approvals/idempotency/audit) is **Postgres** (0004/0005 tables) via
`DATABASE_URL` (role `affos_service`) — not SQLite. Migrations run as `affos_owner`; the bootstrap
superuser runs `roles.sql` once. n8n never gets a DB credential.

## Backup / restore
- Backup before migration: `pg_dump "$OWNER_URL" --format=custom -f affos_pre<ts>.dump` (store off-box).
- Restore TEST (prove the snapshot loads before applying 0004), into a fresh/scratch DB:
  `deploy/scripts/pg_restore.sh affos_pre<ts>.dump "<scratch-db-url>"` (no --clean; refuses prod-looking targets).

## Validate (per STAGING_PREP runbook)
`/health` 200 · dry-run `ingest` → `stopped`/NOT YET VERIFIED · `impact` → 403 · restart + idempotency
(200 cached / 409 diff / 409 pending) · approval + revoke + RBAC + audit · WF060 dry-run (n8n).

## Notes / deferred
- The durable approvals/idempotency store uses `AFFOS_INGEST_DB` (SQLite on a volume). A Postgres-backed
  store (using the 0004 tables) is a separate code task.
- n8n is a separate deployment; attach it to the `omi-staging` network (or make the network external)
  so WF060 can reach `affos-runtime:8099`.
- Image build was not verified in CI here (no Docker daemon in the authoring session); `docker compose
  config` is valid and the `server.py` entrypoint was run directly (`/health` 200, unauth → 401).
- AWIN live ingest / Impact production remain OFF — separate approval.
