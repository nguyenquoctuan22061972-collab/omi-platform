#!/usr/bin/env bash
# Wrapper (ADDITIVE, Phase 12 Module D): tên gọi verify-restore.sh → chuyển tiếp
# script restore-verify.sh sẵn có (dry-run restore, KHÔNG đụng ./data). Single source of truth.
# Usage: deploy/backup/verify-restore.sh <archive.tar.gz>
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$DIR/restore-verify.sh" "$@"
