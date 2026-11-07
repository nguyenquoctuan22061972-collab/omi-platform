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
# Apply migration 0004 to the staging Postgres BEFORE the LIVE report/reconcile path (see the
# apply-0004 runbook: backup → duplicate pre-check → apply → verify).
```

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
