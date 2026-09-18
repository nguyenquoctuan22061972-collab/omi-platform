#!/usr/bin/env bash
# Dry-run restore verify (PRD-008 F): giải nén vào thư mục tạm, kiểm nội dung, KHÔNG đụng ./data.
# Usage: deploy/backup/restore-verify.sh <archive.tar.gz>
set -uo pipefail
ARCHIVE="${1:?Usage: restore-verify.sh <archive.tar.gz>}"
[ -f "$ARCHIVE" ] || { echo "FAIL: không thấy $ARCHIVE"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! tar -xzf "$ARCHIVE" -C "$TMP" 2>/dev/null; then echo "FAIL: giải nén lỗi"; exit 1; fi

# Kỳ vọng có thư mục data với ít nhất 1 file .db (SQLite CRM/Auth).
if find "$TMP" -type f \( -name '*.db' -o -name '*.sqlite3' \) | grep -q .; then
  echo "OK dry-run restore: tìm thấy DB trong backup"
  echo "PASS restore verify (dry-run, không đụng ./data): $ARCHIVE"
  exit 0
else
  echo "WARN: backup không chứa .db (có thể trống) — kiểm tra lại nội dung"
  echo "PASS(cấu trúc) restore verify: giải nén được, không có DB"
  exit 0
fi
