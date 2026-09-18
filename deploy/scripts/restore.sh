#!/usr/bin/env bash
# Restore SQLite volume từ backup (PRD-005 §6). Usage: deploy/scripts/restore.sh <archive.tar.gz>
set -euo pipefail

ARCHIVE="${1:?Usage: restore.sh <archive.tar.gz>}"
DATA_DIR="${DATA_DIR:-./data}"
COMPOSE="deploy/docker-compose.prod.yml"

[ -f "$ARCHIVE" ] || { echo "ERROR: không thấy '$ARCHIVE'" >&2; exit 1; }

echo "Dừng service ứng dụng…"
docker compose -f "$COMPOSE" stop crm-core auth-rbac || true

echo "Sao lưu data hiện tại trước khi restore…"
[ -d "$DATA_DIR" ] && mv "$DATA_DIR" "${DATA_DIR}.pre-restore.$(date -u +%s)" || true

echo "Giải nén $ARCHIVE …"
mkdir -p "$(dirname "$DATA_DIR")"
tar -xzf "$ARCHIVE" -C "$(dirname "$DATA_DIR")"

echo "Khởi động lại service…"
docker compose -f "$COMPOSE" up -d crm-core auth-rbac
echo "Restore xong. Chạy deploy/scripts/healthcheck.sh để xác nhận."
