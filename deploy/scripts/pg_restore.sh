#!/usr/bin/env bash
# AFFOS logical restore — companion to `pg_dump --format=custom`. OPS tool; run on the host.
# For the pre-migration restore TEST into a fresh/scratch staging DB. NEVER touches production.
#
# Usage:
#   deploy/scripts/pg_restore.sh <dump-file> <target-database-url>
#
# Safety:
#   * ALLOWLIST: the target must match AFFOS_RESTORE_ALLOW (default: name contains 'scratch' or
#     'staging'). Anything else is refused — a restore cannot be pointed at an arbitrary/prod DB.
#   * Refuses a target whose name looks like production.
#   * --single-transaction: a partial/failed restore ROLLS BACK (no half-restored DB).
#   * No --clean: existing objects are never dropped.
set -euo pipefail

DUMP="${1:?usage: pg_restore.sh <dump-file> <target-database-url>}"
TARGET="${2:?usage: pg_restore.sh <dump-file> <target-database-url>}"
ALLOW="${AFFOS_RESTORE_ALLOW:-(scratch|staging)}"

[ -f "$DUMP" ] || { echo "ERROR: dump file not found: $DUMP" >&2; exit 1; }
command -v pg_restore >/dev/null || { echo "ERROR: pg_restore not installed" >&2; exit 1; }

# Match on the DATABASE NAME only (not the whole URL — a host/socket path must not fool the guard).
_nodb="${TARGET%%\?*}"      # strip any ?query
DBNAME="${_nodb##*/}"       # last path segment == database name (or the bare name if not a URL)

# 1) Deny production-looking database names outright.
case "$DBNAME" in
  *prod*|*production*) echo "ERROR: target database '$DBNAME' looks like production; refuse." >&2; exit 2 ;;
esac
# 2) Allowlist: the database NAME must match AFFOS_RESTORE_ALLOW (scratch/staging by default).
if ! printf '%s' "$DBNAME" | grep -Eq "$ALLOW"; then
  echo "ERROR: database '$DBNAME' does not match AFFOS_RESTORE_ALLOW='$ALLOW' — refusing (use a scratch/staging DB)." >&2
  exit 3
fi

echo "Restoring: $DUMP"
echo "Target   : matches allowlist '$ALLOW' (value not printed)"
echo "Mode     : --single-transaction (rolls back on error), no --clean."

# --no-owner/--no-privileges so the dump loads regardless of role names on the scratch DB;
# --single-transaction + --exit-on-error so a partial restore is atomic and a hard failure.
pg_restore --no-owner --no-privileges --single-transaction --exit-on-error \
  --dbname "$TARGET" "$DUMP"

echo "RESTORE OK. Verify row counts (e.g. commissions/conversion_events) before trusting the snapshot."
