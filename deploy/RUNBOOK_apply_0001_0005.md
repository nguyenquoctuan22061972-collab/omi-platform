# RUNBOOK — apply migrations 0001→0005 (dedicated staging Postgres, Option A)

**Audience:** a human operator applying the AFFOS schema to the **dedicated, production-independent staging PostgreSQL**
(Option A). **DRY-RUN posture; Impact OFF; AWIN live OFF.** This runbook applies migrations to a real staging DB; it does
**not** enable any live affiliate path, run paid calls, or deploy the content pipeline.

**Apply from** a checkout that contains `deploy/postgres/roles.sql`, `AFFOS/core/schema/0001–0005`, and
`deploy/scripts/pg_restore.sh`. **Golden rule:** every step is additive + idempotent; stop at any ✅ gate that fails — the
Step‑1 backup is the safety net. Secrets come from the secret store and must never be echoed into logs, files, or the repo.

---

## 0. Preconditions & inputs
- PostgreSQL **16** reachable; `psql`, `pg_dump`, `pg_restore` on the operator host.
- A **scratch/throwaway** staging DB name for the restore test (name must contain `scratch` or `staging` — `pg_restore.sh`
  enforces this).
- Secrets (never printed/committed): `SUPERUSER_URL` (bootstrap superuser), `AFFOS_PG_OWNER_PASSWORD`,
  `AFFOS_PG_SERVICE_PASSWORD`. Non-secret: `AFFOS_PG_DB` (e.g. `affos_staging`).
- Derived URLs (kept in the shell only, not in logs):
  - `OWNER_URL=postgresql://affos_owner:$AFFOS_PG_OWNER_PASSWORD@<host>:5432/$AFFOS_PG_DB`
  - `SVC_URL=postgresql://affos_service:$AFFOS_PG_SERVICE_PASSWORD@<host>:5432/$AFFOS_PG_DB`
- A change window and an operator who can restore. **Confirm this is the staging DB (not prod) before anything.**

## 1. Backup (pre-apply safety net) — MANDATORY
```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
pg_dump "$OWNER_URL" --format=custom -f "affos_pre_$TS.dump"
# copy affos_pre_$TS.dump off-box; record its path + sha256sum
```
✅ Gate: dump exists, non-zero, `sha256sum` recorded. **Do not proceed without a stored backup.**

## 2. Restore TEST — prove the backup loads (into a FRESH scratch DB, never prod)
```bash
psql "$SUPERUSER_URL" -c "CREATE DATABASE affos_restore_scratch;"   # name must contain scratch/staging
deploy/scripts/pg_restore.sh "affos_pre_$TS.dump" \
  "postgresql://<owner-or-super>:<pw>@<host>:5432/affos_restore_scratch"
```
`pg_restore.sh` guards: prod-looking names → exit 2; outside the scratch/staging allowlist → exit 3; `--single-transaction`
(atomic). ✅ Gate: exit 0; spot-check row counts. Drop the scratch DB afterward.

## 3. Duplicate / idempotency pre-check (only the FIRST time 0004 is applied)
`0004` creates `UNIQUE(source, source_record_id)` on `commissions`, `conversion_events`, `click_events`. Existing
duplicates make index creation fail — check first:
```bash
for t in commissions conversion_events click_events; do
  psql "$OWNER_URL" -tc "SELECT source, source_record_id, COUNT(*) FROM $t
    GROUP BY source, source_record_id HAVING COUNT(*)>1 LIMIT 5;"
done
```
✅ Gate: **no rows** for any table. If duplicates exist, STOP and reconcile before applying 0004. (If 0004 is already
applied, the indexes exist and this check is a no-op.)

## 4. Bootstrap roles — ONCE, as the superuser, BEFORE migrations
`roles.sql` is secret-free + idempotent: it creates `anon/authenticated/service_role` (service_role keeps BYPASSRLS for the
deferred financial path — **no runtime role is a member**), the `affos_owner` (DDL/migrations) and the least-privilege
`affos_service` (runtime; **no BYPASSRLS, not in service_role, no DDL**).
```bash
psql "$SUPERUSER_URL" -v ON_ERROR_STOP=1 -f deploy/postgres/roles.sql
# set LOGIN passwords OUT OF BAND (values from the secret store; never in a file/log):
psql "$SUPERUSER_URL" -v owner_pw="$AFFOS_PG_OWNER_PASSWORD" -c "alter role affos_owner   password :'owner_pw';"
psql "$SUPERUSER_URL" -v svc_pw="$AFFOS_PG_SERVICE_PASSWORD" -c "alter role affos_service password :'svc_pw';"
```
✅ Gate:
```bash
psql "$SUPERUSER_URL" -tc "SELECT rolname, rolcanlogin, rolbypassrls FROM pg_roles
  WHERE rolname IN ('affos_owner','affos_service','service_role');"
```
→ `affos_owner` login t / bypassrls f; `affos_service` login t / **bypassrls f**; `service_role` bypassrls t.

## 5. Apply migrations 0001→0005 — as `affos_owner`, in order, ON_ERROR_STOP
```bash
for f in 0001_affos_core 0002_rls 0003_provenance 0004_revenue_ingest 0005_ingest_store_policies; do
  echo "applying $f"
  psql "$OWNER_URL" -v ON_ERROR_STOP=1 -f "AFFOS/core/schema/$f.sql" || { echo "FAILED at $f"; exit 1; }
done
```
Expected: zero errors (on a re-run, only idempotent NOTICEs such as `DROP POLICY IF EXISTS …`). ✅ Gate: every file exits 0.

## 6. VERIFY (acceptance checks)
**6a. Schema**
```bash
psql "$OWNER_URL" -tc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"   # expect 23
psql "$OWNER_URL" -tc "SELECT indexname FROM pg_indexes WHERE indexname LIKE 'ux_%_src';"             # ux_{commissions,conversion_events,click_events}_src
psql "$OWNER_URL" -tc "SELECT polname FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid WHERE c.relname='audit_logs';"  # incl. audit_logs_ins_service
```
**6b. Least-privilege privilege matrix — connect as `affos_service` (`SVC_URL`):**

| Operation | Target | Expected |
|---|---|---|
| INSERT | `audit_logs` (`event='cost.call'` row) | **ALLOW** (policy `audit_logs_ins_service`) |
| INSERT / UPDATE | `ingestion_approvals`, `ingestion_idempotency` | ALLOW |
| UPDATE / DELETE | `audit_logs` | **DENY** |
| INSERT | `commissions` (financial) | **DENY** |
| INSERT | `agent_runs`, `system_events` | **DENY** (no grant yet — by design) |
| CREATE / ALTER TABLE (DDL) | — | **DENY** |
| role attrs | `affos_service` | `rolbypassrls=f`, `rolsuper=f`, **not** a member of `service_role` |

✅ Gate: every row matches.

## 7. Point the runtime at the DB (service deploy — separate from migration)
Set `DATABASE_URL=$SVC_URL` for `affos-runtime` (`deploy/docker-compose.staging.yml` already derives it as the
least-privilege `affos_service`). Migrations run as `affos_owner`; the runtime connects as `affos_service`; **n8n gets no DB
credential.** Post-deploy dry-run smoke: `/health` → 200; unauthenticated ingest → 401; dry-run ingest → `stopped`/NOT YET
VERIFIED; `impact` → 403.

## 8. ROLLBACK
- **Permission/policy only (0005):** `REVOKE INSERT, UPDATE, SELECT ON <t> FROM affos_service;` + `DROP POLICY <name> ON <t>;`
  — additive, no data change.
- **Full rollback:** restore from the Step‑1 backup into the target (the Step‑2 restore test already proved the dump loads).
- Migrations are additive (`CREATE … IF NOT EXISTS`, `DROP POLICY IF EXISTS` → `CREATE`); re-apply is safe. **No destructive
  DDL on data in 0001–0005.**

## 9. GO / NO-GO
Proceed to the next step only when its ✅ gate passes. **ABORT** (and restore if needed) if: backup missing (Step 1),
restore test non-zero (Step 2), duplicates found (Step 3), a migration errors (Step 5), or any privilege-matrix row is wrong
(Step 6). Record the outcome of each gate.

---
## Scope / limits
- This runbook applies migrations to a real staging DB only. **AWIN live and Impact production remain OFF** (separate
  approval); no paid calls; no content-pipeline deploy.
- The **5 paid baseline runs** and the pilot wiring are **separate approvals**, after this DB is up.
- The verification expectations (23 tables; privilege matrix) were observed on a disposable scratch PostgreSQL 16; the
  operator must confirm them on the real staging DB. A static runbook is not a production-readiness claim.
