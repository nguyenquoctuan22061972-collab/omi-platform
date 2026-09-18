#!/usr/bin/env bash
# Backup verify + checksum (PRD-008 F). KHÔNG ghi đè deploy/scripts/backup.sh.
# Usage: deploy/backup/backup-verify.sh <archive.tar.gz>
set -uo pipefail
ARCHIVE="${1:?Usage: backup-verify.sh <archive.tar.gz>}"

[ -f "$ARCHIVE" ] || { echo "FAIL: không thấy $ARCHIVE"; exit 1; }

# 1. Toàn vẹn gzip/tar
if ! gzip -t "$ARCHIVE" 2>/dev/null; then echo "FAIL: gzip hỏng"; exit 1; fi
if ! tar -tzf "$ARCHIVE" >/dev/null 2>&1; then echo "FAIL: tar không đọc được"; exit 1; fi

# 2. Checksum (ghi sidecar .sha256 nếu chưa có; nếu có thì verify)
SUM_FILE="$ARCHIVE.sha256"
if command -v sha256sum >/dev/null 2>&1; then SUM=$(sha256sum "$ARCHIVE" | awk '{print $1}');
else SUM=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}'); fi
if [ -f "$SUM_FILE" ]; then
  if grep -q "$SUM" "$SUM_FILE"; then echo "OK checksum khớp"; else echo "FAIL checksum lệch"; exit 1; fi
else
  echo "$SUM  $(basename "$ARCHIVE")" > "$SUM_FILE"; echo "OK checksum ghi mới: $SUM_FILE"
fi

echo "PASS backup verify: $ARCHIVE"
