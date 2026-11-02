# AFFOS Production Runtime (SPRINT 01)

Minimal, **additive** runtime for AFFOS. It does **not** modify the `omi` compose stack,
the n8n stack, CRM Core, WF050, the DB schema, or RLS. It adds a small health/service
process and the wiring needed to select a repository and (later, when approved) ingest AWIN
transactions into Postgres.

## 1. Deployment architecture

```
            ┌───────────────────────────── VPS ─────────────────────────────┐
            │  n8n_data_n8n-network                                          │
            │   ┌──────────┐      ┌───────────────┐                          │
            │   │ postgres │◄─────┤ affos-runtime │  (NEW, this sprint)      │
            │   │  :5432   │      │   :8099 /health│                          │
            │   └──────────┘      └───────────────┘                          │
            │  omi network: crm-core, auth-rbac, nginx, certbot (UNCHANGED)  │
            └────────────────────────────────────────────────────────────────┘
```

- `affos-runtime` is a **standalone container** (image built from `AFFOS/Dockerfile`).
- It must **join the existing external network `n8n_data_n8n-network`** to reach `postgres`
  by service name. It does **not** modify that network or any existing compose file.

## 2. Environment variables

| Var | Required | Purpose |
|-----|----------|---------|
| `AFFOS_RUNTIME_PORT` | no (default `8099`) | health/service port |
| `DATABASE_URL` or `SUPABASE_DB_URL` | for LIVE | Postgres DSN; **presence** switches repository_mode to LIVE |
| `AWIN_API_TOKEN`, `AWIN_PUBLISHER_ID` | for AWIN LIVE (future) | AWIN auth — **env secret only**, never in source/Git |

- DB DSN format: `postgresql://affos_app:********@postgres:5432/affos`
  (service name `postgres`, **not** `127.0.0.1` — the DB is host-bound to 127.0.0.1:5432,
  so a container must reach it over the shared Docker network, not the host loopback).
- Secrets are injected by the environment/secret store only. The health endpoint reports
  **mode**, never values.

## 3. Network dependency

- `postgres` is on `n8n_data_n8n-network` and bound to `127.0.0.1:5432` on the host.
- Therefore the runtime container **must** attach to `n8n_data_n8n-network` and use host
  `postgres:5432`. Running on the host (not containerized) would instead use `127.0.0.1:5432`.

## 4. Repository wiring

- `runtime.build_repository(env)` → `core.repository.select_repository(env)`:
  - no DB URL → **SqliteRepository (DRY-RUN)** — existing behavior preserved.
  - DB URL set → **PostgresRepository (LIVE / PRODUCTION_VERIFIED only)**.
- The **seed pipeline** (`core/pipeline.py`) stays DRY-RUN/SQLite by design (SQLite paramstyle,
  SEEDED data). The **LIVE Postgres write path** is AWIN ingestion
  (`runtime/awin_ingest.py` → `connectors/awin/awin_live.ingest_transactions`), not the seed
  pipeline. `pipeline.run(..., repo=...)` now accepts an injected repo (backward compatible).

## 5. AWIN caller (prepared, NOT executed this sprint)

`runtime/awin_ingest.run_ingestion(env, start, end, approved, transport)` is gated:
it STOPS unless `approved=True` **and** repository_mode is LIVE **and** a production transport
is supplied. No live AWIN call is made in this sprint; proof stays `NOT YET VERIFIED`.

## 6. Startup procedure (operator, on the VPS — not run by Builder)

```bash
# build image from the AFFOS directory
cd /opt/omi-platform/AFFOS
docker build -t affos-runtime:sprint-01 .

# DRY-RUN (no DB): health reports repository_mode=DRY-RUN
docker run -d --name affos-runtime --restart unless-stopped \
  -e AFFOS_RUNTIME_PORT=8099 -p 127.0.0.1:8099:8099 \
  affos-runtime:sprint-01

# LIVE wiring (when approved): join the DB network and pass the DSN via env/secret
docker run -d --name affos-runtime --restart unless-stopped \
  --network n8n_data_n8n-network \
  -e AFFOS_RUNTIME_PORT=8099 -p 127.0.0.1:8099:8099 \
  -e DATABASE_URL="postgresql://affos_app:********@postgres:5432/affos" \
  affos-runtime:sprint-01

curl -s http://127.0.0.1:8099/health     # {"repository_mode":"DRY-RUN"|"LIVE", ...}
```

## 7. Rollback procedure

```bash
docker stop affos-runtime && docker rm affos-runtime
# optional: docker rmi affos-runtime:sprint-01
```
- Purely additive: removing the container restores the prior state. No schema, RLS, compose,
  n8n, or CRM changes are made, so there is nothing else to revert.

## 8. Safety notes

- No `CREATE DATABASE/USER`, no migration, no RLS change, no compose/n8n/WF050 change.
- No AWIN live call; no secret in source or logs. Health endpoint is secret-free and does
  not open a DB connection.
