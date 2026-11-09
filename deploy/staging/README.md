# AFFOS Staging Verification Suite (Milestone 2, TASK 3)

Run **on the staging host, after** `deploy/RUNBOOK_apply_0001_0005.md` has applied migrations 0001–0005.
Everything here is **read-mostly and DRY-RUN**: no paid provider call, no live affiliate call, and the one
DB write (`verify_db.py`'s `cost.call` INSERT) is **rolled back**. No secret/URL is printed.

## 1. Database checks — `verify_db.py`
```bash
export AFFOS_OWNER_URL='postgresql://affos_owner:***@<host>:5432/affos_staging'     # from secret store
export AFFOS_SERVICE_URL='postgresql://affos_service:***@<host>:5432/affos_staging'  # from secret store
python3 deploy/staging/verify_db.py        # prints PASS/FAIL per check; exit 0 iff all PASS
```
Checks: PostgreSQL 16 · 23 tables · RLS on all · `ux_*_src` indexes · `audit_logs` policies ·
`affos_service` not super / not BYPASSRLS / in `authenticated` not `service_role` · grants (audit_logs =
SELECT+INSERT, financial = SELECT only) · **live matrix as `affos_service`**: INSERT `cost.call` ALLOW;
UPDATE/DELETE `audit_logs` DENY (42501); INSERT financial DENY (42501); CREATE TABLE DENY (42501).

> Proven correct on a disposable scratch PostgreSQL 16 (**15/15 PASS**). The operator confirms the same on
> the real staging DB — a scratch result is **not** a staging-readiness claim.

## 2. Runtime checks — `verify_http.sh`
```bash
BASE_URL=http://localhost:8099 deploy/staging/verify_http.sh
```
Checks: `/health` liveness 200 · `/ready` readiness 200 (DB up) · unauthenticated ingest → **401** (JWT
`iss`/`aud` enforced). Plus operator-driven negatives with Postgres stopped: `/ready` → **503**, authed
ingest → **503** (no false success, no SQLite downgrade), then reconnect on restart.

## 2b. Static security check — `verify_security.py` (no DB; CI-safe)
```bash
python3 deploy/staging/verify_security.py   # 10 checks: no public PG port, runtime=affos_service,
                                            # no n8n DB creds, roles.sql least-privilege, no committed secret
```

## 2c. Scratch-PG rehearsals (self-contained; build + destroy their own PostgreSQL 16)
```bash
deploy/staging/backup_restore_rehearsal.sh   # dump → checksum → restore → verify (no data loss). 13 gates.
deploy/staging/migration_safety_rehearsal.sh # order/idempotency/duplicate-precheck/unique-index. 8 gates.
```
> Run end-to-end on a disposable scratch PostgreSQL 16 (**backup/restore 13/13, migration 8/8 PASS**).
> They NEVER connect to staging/production and clean up after themselves.

## 3. Network / volume / isolation (host-level, operator checks)
- `docker compose -f deploy/docker-compose.staging.yml ps` → Postgres has **no published host port** (internal
  `omi-staging` bridge only). `.env.staging` is gitignored; secrets come from the secret store.
- Volumes `./staging-data/{pg,auth,affos}` are the staging DB/auth/runtime data, **independent of prod**.

## Mapping to Milestone-2 acceptance criteria
| Criterion | Verified by |
|---|---|
| Staging exists & independent | §3 (compose up on the host; separate volumes/network) |
| Backup/restore | `RUNBOOK` steps 1–2 + `deploy/scripts/pg_restore.sh` (scratch restore test) |
| Migrations 0001–0005 applied in order | `RUNBOOK` step 5 + `verify_db.py` (23 tables/indexes/policies) |
| RLS + privilege matrix | `verify_db.py` (live 42501 denials) |
| Runtime uses `affos_service`; n8n no DB creds | `verify_db.py` (current_user) + compose (`DATABASE_URL` = affos_service; n8n absent) |
| JWT `iss`/`aud` enforced | `verify_http.sh` (401) + compose env |
| API 503 when DB unavailable | `verify_http.sh` operator negative (`/ready` 503, ingest 503) |
| Cost/live-mode guard | offline `test_fullchain_integration` + `AFFOS_PROVIDERS_LIVE` OFF (secrets-manifest) |

**None of this is PASS until it is run on the real staging host and recorded.** Scratch/offline evidence
only proves the suite and the code are correct.
