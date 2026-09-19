#!/usr/bin/env bash
# Daily backup runtime (PRD-012 D): backup → verify checksum → rotation.
# Không ghi đè script cũ; gọi lại deploy/scripts/backup.sh + deploy/backup/backup-verify.sh.
# Usage: BACKUP_DIR=./backups BACKUP_KEEP=14 deploy/backup/daily-backup.sh
set -uo pipefail
cd "$(dirname "$0")/../.." 2>/dev/null || true

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${BACKUP_KEEP:-14}"
log() { echo "[daily-backup] $*"; }

# 1. Tạo backup (script sẵn có, đã tự rotation theo KEEP).
if ! BACKUP_DIR="$BACKUP_DIR" BACKUP_KEEP="$KEEP" bash deploy/scripts/backup.sh; then
  log "FAIL tạo backup"; exit 1
fi

# 2. Verify bản mới nhất (checksum + toàn vẹn).
LATEST="$(ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz 2>/dev/null | head -1 || true)"
if [ -z "$LATEST" ]; then log "FAIL không thấy backup vừa tạo"; exit 1; fi
if ! bash deploy/backup/backup-verify.sh "$LATEST"; then
  log "FAIL verify $LATEST"; exit 1
fi

# 3. Rotation phòng hờ (giữ N bản, xoá cũ hơn).
ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz 2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f
ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz.sha256 2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f

log "OK daily backup: $LATEST (giữ $KEEP bản)"
