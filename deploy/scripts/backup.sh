#!/usr/bin/env bash
# Backup data (PRD-005 §6). ADDITIVE — hai chế độ, chọn theo env, không đổi hành vi cũ:
#   - PG_VOLUME đặt  -> backup Docker volume PostgreSQL thực tế (read-only, không đụng /data)
#   - PG_VOLUME rỗng -> backup filesystem DATA_DIR (mặc định ./data — giữ tương thích cũ)
# Usage:
#   BACKUP_DIR=./backups deploy/scripts/backup.sh
#   PG_VOLUME=n8n_data_postgres_data BACKUP_DIR=./backups deploy/scripts/backup.sh
set -euo pipefail

DATA_DIR="${DATA_DIR:-./data}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${BACKUP_KEEP:-14}"
PG_VOLUME="${PG_VOLUME:-}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$BACKUP_DIR"
ABS_BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"
ARCHIVE="$BACKUP_DIR/omi-backup-$TS.tar.gz"

if [ -n "$PG_VOLUME" ]; then
  # ---- Docker volume mode (PostgreSQL data volume thực tế) ----
  command -v docker >/dev/null 2>&1 || { echo "ERROR: PG_VOLUME đặt nhưng không có docker" >&2; exit 1; }
  if ! docker volume inspect "$PG_VOLUME" >/dev/null 2>&1; then
    echo "ERROR: docker volume '$PG_VOLUME' không tồn tại" >&2; exit 1
  fi
  # Chọn helper image đã có sẵn (ưu tiên image container postgres → KHÔNG cần pull/cài mới).
  HELPER_IMAGE="${BACKUP_HELPER_IMAGE:-}"
  if [ -z "$HELPER_IMAGE" ]; then
    PG_CT="$(docker ps --filter 'name=postgres' --format '{{.Names}}' 2>/dev/null | head -1)"
    [ -n "$PG_CT" ] && HELPER_IMAGE="$(docker inspect --format '{{.Config.Image}}' "$PG_CT" 2>/dev/null || true)"
  fi
  HELPER_IMAGE="${HELPER_IMAGE:-alpine:3}"
  # Mount volume READ-ONLY; không tắt/đụng container postgres đang chạy.
  if ! docker run --rm \
        -v "$PG_VOLUME":/vol:ro \
        -v "$ABS_BACKUP_DIR":/backup \
        "$HELPER_IMAGE" \
        tar -czf "/backup/omi-backup-$TS.tar.gz" -C /vol . ; then
    echo "ERROR: backup docker volume '$PG_VOLUME' thất bại" >&2; exit 1
  fi
  echo "Backup (volume $PG_VOLUME, image $HELPER_IMAGE): $ARCHIVE"
else
  # ---- Filesystem mode (tương thích cũ: SQLite ./data) ----
  if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: data dir '$DATA_DIR' không tồn tại" >&2; exit 1
  fi
  tar -czf "$ARCHIVE" -C "$(dirname "$DATA_DIR")" "$(basename "$DATA_DIR")"
  echo "Backup: $ARCHIVE"
fi

# Giữ N bản mới nhất, xoá cũ hơn.
ls -1t "$BACKUP_DIR"/omi-backup-*.tar.gz 2>/dev/null | tail -n +"$((KEEP+1))" | xargs -r rm -f
echo "Giữ $KEEP bản gần nhất."
