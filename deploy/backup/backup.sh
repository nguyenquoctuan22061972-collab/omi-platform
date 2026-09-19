#!/usr/bin/env bash
# Wrapper (ADDITIVE): chuyển tiếp sang script backup chuẩn deploy/scripts/backup.sh.
# Cho phép gọi backup theo cả hai đường dẫn; TOÀN BỘ logic nằm 1 chỗ (single source of truth):
#   - PG_VOLUME đặt  -> mount volume :ro, tar qua helper dùng image container postgres (không pull mới)
#   - PG_VOLUME rỗng -> giữ nguyên nhánh DATA_DIR (./data) cũ
# Mọi env (PG_VOLUME, BACKUP_DIR, BACKUP_KEEP, DATA_DIR...) và tham số được kế thừa nguyên vẹn.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$DIR/scripts/backup.sh" "$@"
