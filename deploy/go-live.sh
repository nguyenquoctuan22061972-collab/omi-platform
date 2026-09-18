#!/usr/bin/env bash
# Zero-downtime go-live (PRD-007 D): preflight → backup → deploy → healthcheck → smoke → auto-rollback.
# Usage: deploy/go-live.sh [image_tag]
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

COMPOSE="deploy/docker-compose.prod.yml"
TAG="${1:-latest}"
log() { echo "[go-live] $*"; }

# 0. Nạp .env
if [ -f deploy/.env ]; then set -a; . deploy/.env; set +a; fi

# 1. Preflight: env đủ + compose hợp lệ
log "preflight…"
bash deploy/secrets/validate-env.sh || { log "FAIL preflight env"; exit 1; }
docker compose -f "$COMPOSE" config >/dev/null || { log "FAIL compose config"; exit 1; }

# 2. Backup trước khi đổi
log "backup…"
BACKUP_DIR="${BACKUP_DIR:-./backups}" bash deploy/scripts/backup.sh || { log "FAIL backup"; exit 1; }
PREV_TAG="$(cat deploy/.last_good_tag 2>/dev/null || echo latest)"

# 3. Deploy (pull + up, rolling)
log "deploy tag=$TAG…"
IMAGE_TAG="$TAG" docker compose -f "$COMPOSE" pull || true
if ! IMAGE_TAG="$TAG" docker compose -f "$COMPOSE" up -d; then
  log "deploy up thất bại → rollback"; deploy/rollback.sh "$PREV_TAG"; exit 1
fi

# 4. Healthcheck + 5. Smoke
log "post-deploy check…"
if bash deploy/post-deploy-check.sh; then
  echo "$TAG" > deploy/.last_good_tag
  log "GO-LIVE OK (tag=$TAG)"; exit 0
else
  log "post-deploy FAIL → auto-rollback về $PREV_TAG"
  deploy/rollback.sh "$PREV_TAG"; exit 1
fi
