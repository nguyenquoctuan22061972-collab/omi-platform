#!/usr/bin/env bash
# AFFOS logical restore — companion to `pg_dump --format=custom` (see deploy/scripts/backup.sh PG_VOLUME
# mode / the apply-0004 runbook). OPS tool; run on the host. Does NOT touch production.
#
# Usage:
#   deploy/scripts/pg_restore.sh <dump-file> <target-database-url>
#
# Restores a custom-format dump INTO the target database. Intended for the pre-migration restore TEST
# into a fresh/scratch staging DB: it proves the snapshot loads before 0004 is applied. It uses no
# --clean (it will not drop objects) and refuses a target whose name looks like production.
set -euo pipefail

DUMP="${1:?usage: pg_restore.sh <dump-file> <target-database-url>}"
TARGET="${2:?usage: pg_restore.sh <dump-file> <target-database-url>}"

[ -f "$DUMP" ] || { echo "ERROR: dump file not found: $DUMP" >&2; exit 1; }
command -v pg_restore >/dev/null || { echo "ERROR: pg_restore not installed" >&2; exit 1; }

# Safety guard: never restore over something that looks like production.
case "$TARGET" in
  *prod*|*production*) echo "ERROR: target looks like production ('$TARGET'); restore only into a scratch/staging DB." >&2; exit 2 ;;
esac

echo "Restoring: $DUMP"
echo "Into     : (target database URL; value not printed)"
echo "Mode     : no --clean (objects are NOT dropped); use a fresh/scratch DB."

# --no-owner/--no-privileges so the dump loads regardless of role names on the scratch DB;
# --exit-on-error so a partial/failed restore is a hard failure (no silent half-restore).
pg_restore --no-owner --no-privileges --exit-on-error --dbname "$TARGET" "$DUMP"

echo "RESTORE OK. Verify row counts (e.g. commissions/conversion_events) before trusting the snapshot."
