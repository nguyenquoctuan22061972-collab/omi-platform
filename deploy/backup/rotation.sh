#!/usr/bin/env bash
# Backup rotation (ADDITIVE, Phase 12 Module D). Giữ N bản .tar.gz mới nhất + sidecar .sha256,
# xoá cũ hơn. Không tạo backup, không đụng business logic — chỉ dọn thư mục backup.
# Usage: BACKUP_DIR=./backups BACKUP_KEEP=14 deploy/backup/rotation.sh
set -euo pipefail
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${BACKUP_KEEP:-14}"
[ -d "$BACKUP_DIR" ] || { echo "rotation: '$BACKUP_DIR' không tồn tại — bỏ qua"; exit 0; }
ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz        2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f
ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz.sha256 2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f
echo "rotation: giữ $KEEP bản gần nhất trong $BACKUP_DIR"
