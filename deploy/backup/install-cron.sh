#!/usr/bin/env bash
# Cài cron daily-backup (PRD-012 D handoff). Additive; idempotent (không thêm trùng dòng).
# Usage: cd /opt/omi-platform && bash deploy/backup/install-cron.sh [HH:MM mặc định 02:30]
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
AT="${1:-02:30}"
MIN="${AT#*:}"; HOUR="${AT%:*}"
LINE="$MIN $HOUR * * * cd $REPO && BACKUP_DIR=$REPO/backups BACKUP_KEEP=14 bash deploy/backup/daily-backup.sh >> $REPO/backups/cron.log 2>&1"
MARK="# omi-daily-backup"

current="$(crontab -l 2>/dev/null | grep -v "$MARK")"
{ printf '%s\n' "$current"; printf '%s %s\n' "$LINE" "$MARK"; } | sed '/^$/d' | crontab -
echo "Đã cài cron daily-backup lúc $AT:"
crontab -l 2>/dev/null | grep "$MARK"
