#!/usr/bin/env bash
# Rollback deploy về tag trước (PRD-007 D). Usage: deploy/rollback.sh <image_tag>
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

COMPOSE="deploy/docker-compose.prod.yml"
TAG="${1:?Usage: rollback.sh <image_tag>}"
log() { echo "[rollback] $*"; }

if [ -f deploy/.env ]; then set -a; . deploy/.env; set +a; fi

log "rollback về tag=$TAG…"
IMAGE_TAG="$TAG" docker compose -f "$COMPOSE" pull || true
if IMAGE_TAG="$TAG" docker compose -f "$COMPOSE" up -d; then
  if bash deploy/post-deploy-check.sh; then
    echo "$TAG" > deploy/.last_good_tag
    log "ROLLBACK OK (tag=$TAG)"; exit 0
  fi
  log "ROLLBACK: service lên nhưng healthcheck vẫn fail — cần can thiệp thủ công (xem runbook)"; exit 2
fi
log "ROLLBACK thất bại — cần can thiệp thủ công (docs/Operations/production-runbook.md)"; exit 1
