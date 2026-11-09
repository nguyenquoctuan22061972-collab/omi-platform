#!/usr/bin/env bash
# AFFOS BACKUP/RESTORE REHEARSAL (Milestone 2, TASK 2) — runs entirely on a DISPOSABLE scratch
# PostgreSQL 16 that this script creates and destroys. It NEVER connects to staging or production.
#
# Flow: scratch cluster -> roles -> migrations 0001-0005 -> seed non-sensitive data -> pg_dump (custom)
#   -> sha256 checksum -> restore into a FRESH scratch DB (via deploy/scripts/pg_restore.sh) -> verify
#   schema/indexes/constraints/RLS + row counts (no data loss) + runtime-role privileges -> cleanup.
# Prints PASS/FAIL per gate; exit 0 iff all PASS. Safe to run in CI or on an operator box with PG16.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PGBIN="$(pg_config --bindir 2>/dev/null || echo /usr/lib/postgresql/16/bin)"
BASE="$(mktemp -d "${TMPDIR:-/tmp}/affos_brr.XXXXXX")"
pass=0; fail=0
ok(){ if [ "$1" = "0" ] || [ "$1" = "PASS" ]; then echo "[PASS] $2"; pass=$((pass+1)); else echo "[FAIL] $2  (${3:-})"; fail=$((fail+1)); fi; }

# --- run postgres as a non-root user (initdb/postgres refuse root). Reuse current user when non-root. ---
RUNUSER=""
if [ "$(id -u)" = "0" ]; then
  id pgscratch >/dev/null 2>&1 || useradd -M -s /usr/sbin/nologin pgscratch
  chown -R pgscratch:pgscratch "$BASE"; chmod 700 "$BASE"
  RUNUSER="runuser -u pgscratch --"
fi
AS(){ $RUNUSER "$@"; }
cleanup(){ AS "$PGBIN/pg_ctl" -D "$BASE/d" -m immediate -w stop >/dev/null 2>&1 || true; rm -rf "$BASE"; }
trap cleanup EXIT

mkdir -p "$BASE/d" "$BASE/s"; [ -n "$RUNUSER" ] && chown -R pgscratch:pgscratch "$BASE"
AS "$PGBIN/initdb" -D "$BASE/d" --encoding=UTF8 --locale=C -A trust -U postgres >/dev/null 2>&1
{ echo "unix_socket_directories = '$BASE/s'"; echo "listen_addresses = ''"; echo "fsync = off"; } >> "$BASE/d/postgresql.conf"
AS "$PGBIN/pg_ctl" -D "$BASE/d" -l "$BASE/pg.log" -w start >/dev/null 2>&1
PSQL(){ AS psql -h "$BASE/s" -U postgres -v ON_ERROR_STOP=1 "$@"; }

echo "== AFFOS backup/restore rehearsal (scratch PG16) =="
PSQL -d postgres -c "create database affos_staging_scratch;" >/dev/null 2>&1
PSQL -d postgres -c "create extension if not exists pgcrypto;" >/dev/null 2>&1
PSQL -d affos_staging_scratch -c "create extension if not exists pgcrypto;" >/dev/null 2>&1
PSQL -d affos_staging_scratch -f "$REPO/deploy/postgres/roles.sql" >/dev/null 2>&1
PSQL -d affos_staging_scratch -c "alter role affos_owner password 'x'; alter role affos_service password 'x';" >/dev/null 2>&1
mig_ok=0
for m in 0001_affos_core 0002_rls 0003_provenance 0004_revenue_ingest 0005_ingest_store_policies; do
  AS psql -h "$BASE/s" -U affos_owner -d affos_staging_scratch -v ON_ERROR_STOP=1 -f "$REPO/AFFOS/core/schema/$m.sql" >/dev/null 2>&1 || mig_ok=1
done
ok "$mig_ok" "migrations 0001-0005 applied in order"

# --- seed NON-SENSITIVE test data (synthetic) ---
PSQL -d affos_staging_scratch >/dev/null 2>&1 <<'SQL'
insert into channels(platform,handle,owner) values ('youtube','@demo','seed');
insert into revenue(source,amount,currency) values ('rehearsal_seed', 100.00, 'VND'), ('rehearsal_seed', 250.50, 'VND');
insert into audit_logs(event,actor,target,meta) values ('seed.event','seed','t','{}'::jsonb);
SQL
SRC_REV=$(PSQL -tAq -d affos_staging_scratch -c "select count(*) from revenue;")
SRC_TABLES=$(PSQL -tAq -d affos_staging_scratch -c "select count(*) from pg_tables where schemaname='public';")

# --- backup (pg_dump custom) + checksum ---
DUMP="$BASE/affos_pre.dump"
AS "$PGBIN/pg_dump" -h "$BASE/s" -U postgres -d affos_staging_scratch --format=custom -f "$DUMP" >/dev/null 2>&1
[ -s "$DUMP" ]; ok "$?" "pg_dump custom format produced a non-empty backup"
SUM1=$(sha256sum "$DUMP" | awk '{print $1}'); SUM2=$(sha256sum "$DUMP" | awk '{print $1}')
[ "$SUM1" = "$SUM2" ] && [ -n "$SUM1" ]; ok "$?" "backup sha256 checksum recorded (${SUM1:0:16}...)"

# --- restore into a FRESH scratch DB via the guarded restore script ---
PSQL -d postgres -c "create database affos_restore_scratch;" >/dev/null 2>&1
PSQL -d affos_restore_scratch -c "create extension if not exists pgcrypto;" >/dev/null 2>&1
if [ -n "$RUNUSER" ]; then chown pgscratch:pgscratch "$DUMP"; fi
AS env AFFOS_RESTORE_ALLOW='(scratch|staging)' bash "$REPO/deploy/scripts/pg_restore.sh" "$DUMP" \
   "postgresql://postgres@/affos_restore_scratch?host=$BASE/s" >/dev/null 2>&1
ok "$?" "pg_restore.sh restored into a fresh scratch DB (guard allowed scratch target)"

# --- verify the restored DB: schema, indexes, constraints, RLS, data (no loss) ---
R_TABLES=$(PSQL -tAq -d affos_restore_scratch -c "select count(*) from pg_tables where schemaname='public';")
[ "$R_TABLES" = "$SRC_TABLES" ] && [ "$R_TABLES" = "23" ]; ok "$?" "restored schema has 23 tables (src=$SRC_TABLES restored=$R_TABLES)"
R_UX=$(PSQL -tAq -d affos_restore_scratch -c "select count(*) from pg_indexes where schemaname='public' and indexname like 'ux_%_src';")
[ "$R_UX" = "3" ]; ok "$?" "restored unique indexes ux_*_src present ($R_UX/3)"
R_RLS=$(PSQL -tAq -d affos_restore_scratch -c "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r' and c.relrowsecurity;")
[ "$R_RLS" = "23" ]; ok "$?" "restored RLS enabled on all 23 tables ($R_RLS/23)"
R_POL=$(PSQL -tAq -d affos_restore_scratch -c "select count(*) from pg_policies where schemaname='public';")
[ "$R_POL" = "28" ]; ok "$?" "restored policies present ($R_POL/28)"
R_REV=$(PSQL -tAq -d affos_restore_scratch -c "select count(*) from revenue;")
[ "$R_REV" = "$SRC_REV" ]; ok "$?" "no data loss — revenue rows src=$SRC_REV restored=$R_REV"

# --- re-establish runtime GRANTs after restore ---
# pg_restore runs with --no-owner --no-privileges (so the dump loads regardless of target role names),
# which means table GRANTs are NOT in the restored DB. A full recovery re-applies the designed grants
# from roles.sql + 0005 (idempotent; no schema/data change) — this is part of the documented procedure.
# NOTE: after a --no-owner restore, objects are owned by the RESTORING SUPERUSER, so grants/policies are
# re-applied as the superuser (not affos_owner). This is documented in the runbook recovery procedure.
PSQL -d affos_restore_scratch -f "$REPO/deploy/postgres/roles.sql" >/dev/null 2>&1
PSQL -d affos_restore_scratch -f "$REPO/AFFOS/core/schema/0005_ingest_store_policies.sql" >/dev/null 2>&1
ok "$?" "runtime grants re-established post-restore as superuser (roles.sql + 0005, idempotent)"

# --- runtime-role privilege correct after restore (affos_service least-privilege) ---
R_BYP=$(PSQL -tAq -d affos_restore_scratch -c "select rolbypassrls from pg_roles where rolname='affos_service';")
[ "$R_BYP" = "f" ]; ok "$?" "restored affos_service has no BYPASSRLS"
DENY=$(AS psql -h "$BASE/s" -U affos_service -d affos_restore_scratch -v VERBOSITY=verbose \
   -c "update audit_logs set actor='x';" 2>&1 | grep -c "42501" || true)
[ "$DENY" = "1" ]; ok "$?" "restored affos_service UPDATE audit_logs DENY (42501)"
ALLOW=$(AS psql -h "$BASE/s" -U affos_service -d affos_restore_scratch \
   -c "insert into audit_logs(event,actor,target,meta) values ('cost.call','v','V0','{}'::jsonb);" 2>&1 | grep -c "INSERT 0 1" || true)
[ "$ALLOW" = "1" ]; ok "$?" "restored affos_service INSERT audit_logs ALLOW"

echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
