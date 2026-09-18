#!/usr/bin/env bash
# Backup SQLite volume (PRD-005 §6). Usage: BACKUP_DIR=./backups deploy/scripts/backup.sh
set -euo pipefail

DATA_DIR="${DATA_DIR:-./data}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${BACKUP_KEEP:-14}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"
if [ ! -d "$DATA_DIR" ]; then
  echo "ERROR: data dir '$DATA_DIR' không tồn tại" >&2; exit 1
fi

ARCHIVE="$BACKUP_DIR/omi-backup-$TS.tar.gz"
tar -czf "$ARCHIVE" -C "$(dirname "$DATA_DIR")" "$(basename "$DATA_DIR")"
echo "Backup: $ARCHIVE"

# Giữ N bản mới nhất, xoá cũ hơn.
ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz 2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f
echo "Giữ $KEEP bản gần nhất."
