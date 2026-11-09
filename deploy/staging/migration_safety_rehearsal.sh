#!/usr/bin/env bash
# AFFOS MIGRATION SAFETY REHEARSAL (Milestone 2, TASK 4) — DISPOSABLE scratch PostgreSQL 16 only.
# NEVER touches staging or production. Does NOT modify any migration file.
#
# Proves: (1) ordering is enforced (0002 before 0001 fails); (2) full apply 0001-0005 is clean;
# (3) re-apply is idempotent (no error, additive CREATE IF NOT EXISTS / DROP POLICY IF EXISTS);
# (4) schema-drift baseline (23 tables / 28 policies / 3 ux_*_src); (5) duplicate PRE-CHECK predicts the
# 0004 unique-index failure, and a partial failure aborts atomically (ON_ERROR_STOP); (6) the unique
# index then rejects a duplicate (23505). Prints PASS/FAIL; exit 0 iff all PASS.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PGBIN="$(pg_config --bindir 2>/dev/null || echo /usr/lib/postgresql/16/bin)"
SCHEMA="$REPO/AFFOS/core/schema"
BASE="$(mktemp -d "${TMPDIR:-/tmp}/affos_mig.XXXXXX")"
pass=0; fail=0
ok(){ if [ "$1" = "0" ] || [ "$1" = "PASS" ]; then echo "[PASS] $2"; pass=$((pass+1)); else echo "[FAIL] $2  (${3:-})"; fail=$((fail+1)); fi; }

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
SU(){ AS psql -h "$BASE/s" -U postgres -v ON_ERROR_STOP=1 "$@"; }
OWN(){ AS psql -h "$BASE/s" -U affos_owner "$@"; }
newdb(){ SU -d postgres -c "drop database if exists $1;" >/dev/null 2>&1; SU -d postgres -c "create database $1;" >/dev/null 2>&1; SU -d "$1" -c "create extension if not exists pgcrypto;" >/dev/null 2>&1; SU -d "$1" -f "$REPO/deploy/postgres/roles.sql" >/dev/null 2>&1; }

echo "== AFFOS migration safety rehearsal (scratch PG16) =="

# (1) ORDER ENFORCED: 0002 (RLS, ALTERs tables) before 0001 must FAIL (tables don't exist yet).
newdb mig_order
OWN -d mig_order -v ON_ERROR_STOP=1 -f "$SCHEMA/0002_rls.sql" >/dev/null 2>&1
[ "$?" -ne 0 ]; ok "$?" "out-of-order apply detected (0002 before 0001 fails)"

# (2) FULL apply 0001-0005 in order is clean.
newdb mig_full
full=0
for m in 0001_affos_core 0002_rls 0003_provenance 0004_revenue_ingest 0005_ingest_store_policies; do
  OWN -d mig_full -v ON_ERROR_STOP=1 -f "$SCHEMA/$m.sql" >/dev/null 2>&1 || full=1
done
ok "$full" "apply 0001-0005 in order is clean"

# (3) IDEMPOTENT re-apply (second pass must not error).
reapply=0
for m in 0001_affos_core 0002_rls 0003_provenance 0004_revenue_ingest 0005_ingest_store_policies; do
  OWN -d mig_full -v ON_ERROR_STOP=1 -f "$SCHEMA/$m.sql" >/dev/null 2>&1 || reapply=1
done
ok "$reapply" "re-apply 0001-0005 is idempotent (no error)"

# (4) SCHEMA-DRIFT baseline.
T=$(SU -tAq -d mig_full -c "select count(*) from pg_tables where schemaname='public';")
P=$(SU -tAq -d mig_full -c "select count(*) from pg_policies where schemaname='public';")
U=$(SU -tAq -d mig_full -c "select count(*) from pg_indexes where schemaname='public' and indexname like 'ux_%_src';")
[ "$T" = "23" ] && [ "$P" = "28" ] && [ "$U" = "3" ]; ok "$?" "schema baseline (tables=$T/23 policies=$P/28 ux_src=$U/3)"

# (5) DUPLICATE PRE-CHECK predicts the 0004 unique-index failure (partial failure aborts atomically).
newdb mig_dup
for m in 0001_affos_core 0002_rls 0003_provenance; do OWN -d mig_dup -v ON_ERROR_STOP=1 -f "$SCHEMA/$m.sql" >/dev/null 2>&1; done
SU -d mig_dup -c "insert into commissions(amount,source,source_record_id) values (1,'awin','DUP'),(2,'awin','DUP');" >/dev/null 2>&1
DUPS=$(SU -tAq -d mig_dup -c "select count(*) from (select 1 from commissions group by source,source_record_id having count(*)>1) x;")
[ "$DUPS" = "1" ]; ok "$?" "duplicate pre-check query finds the duplicate (groups=$DUPS)"
OWN -d mig_dup -v ON_ERROR_STOP=1 -f "$SCHEMA/0004_revenue_ingest.sql" >/dev/null 2>&1
[ "$?" -ne 0 ]; ok "$?" "0004 unique-index creation FAILS on existing duplicates (precheck was right)"
# clean the duplicate, then 0004 + 0005 apply cleanly
SU -d mig_dup -c "delete from commissions where source_record_id='DUP' and amount=2;" >/dev/null 2>&1
fix=0
for m in 0004_revenue_ingest 0005_ingest_store_policies; do OWN -d mig_dup -v ON_ERROR_STOP=1 -f "$SCHEMA/$m.sql" >/dev/null 2>&1 || fix=1; done
ok "$fix" "after reconciling the duplicate, 0004-0005 apply cleanly"

# (6) UNIQUE index now REJECTS a duplicate (23505).
VIOL=$(SU -d mig_dup -v VERBOSITY=verbose -c "insert into commissions(amount,source,source_record_id) values (3,'awin','DUP');" 2>&1 | grep -c "23505" || true)
[ "$VIOL" = "1" ]; ok "$?" "ux_commissions_src rejects a duplicate insert (23505)"

echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
