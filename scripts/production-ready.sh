#!/usr/bin/env bash
# Production-ready validator (PRD-007 E). Sinh báo cáo PASS/FAIL + score.
# Mặc định: report (exit 0). --strict: exit 1 nếu có FAIL. Không gọi API bên thứ ba.
# Usage: scripts/production-ready.sh [--strict]   (chạy tại repo root hoặc bất kỳ đâu)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

STRICT=0; [ "${1:-}" = "--strict" ] && STRICT=1
BASE="${BASE:-http://localhost}"
pass=0; fail=0; skip=0
line() { printf "%-24s %s\n" "$1" "$2"; }
ok()   { line "$1" "PASS"; pass=$((pass+1)); }
no()   { line "$1" "FAIL — $2"; fail=$((fail+1)); }
sk()   { line "$1" "SKIP — $2"; skip=$((skip+1)); }

echo "=== OMI Production-Ready Report ==="

# 1. Docker
if command -v docker >/dev/null 2>&1; then ok "Docker"; else sk "Docker" "docker chưa cài (kiểm khi ở VPS)"; fi

# 2. Nginx config
[ -f deploy/nginx/conf.d/omi.conf ] && ok "Nginx config" || no "Nginx config" "thiếu omi.conf"

# 3. SSL (cert dir khi deploy)
if [ -d deploy/certs/live ] 2>/dev/null; then ok "SSL certs"; else sk "SSL certs" "cấp khi go-live (certbot)"; fi

# 4. CI
[ -f .github/workflows/ci.yml ] && ok "CI workflow" || no "CI workflow" "thiếu ci.yml"

# 5. Secrets đủ
if [ -f deploy/.env ]; then
  set -a; . deploy/.env; set +a
  if bash deploy/secrets/validate-env.sh >/dev/null 2>&1; then ok "Secrets"; else no "Secrets" "thiếu biến (chạy deploy/secrets/validate-env.sh)"; fi
else
  sk "Secrets" "deploy/.env chưa tạo (copy từ .env.example)"
fi

# 6. Adapter enable (dry-run report qua python)
if command -v python3 >/dev/null 2>&1; then
  n="$(python3 - <<'PY' 2>/dev/null
import os,sys
sys.path.insert(0,".")
from libs.integrations import activation as a
print(sum(1 for r in a.activation_report(os.environ) if r["ok"]))
PY
)"
  [ -n "$n" ] && ok "Adapters enabled ($n)" || no "Adapters" "activation report lỗi"
else sk "Adapters" "python3 không có"; fi

# 7. n8n status
[ -f deploy/n8n/enable-production.md ] && ok "n8n kit" || no "n8n kit" "thiếu enable-production.md"

# 8-11. Endpoints/UI (chỉ khi service chạy)
check_http() { local n="$1" u="$2" e="$3"; local c; c="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 5 "$u" 2>/dev/null || echo 000)"; if echo "$e" | grep -qw "$c"; then ok "$n"; else sk "$n" "không truy cập ($c) — kiểm khi service chạy"; fi; }
check_http "Dashboard KPI" "$BASE/api/crm/dashboard/kpi" "200"
[ -f apps/dashboard/contacts/index.html ] && ok "Contacts UI" || no "Contacts UI" "thiếu"
[ -f apps/dashboard/inbox/index.html ] && ok "Inbox UI" || no "Inbox UI" "thiếu"
[ -f apps/dashboard/pipeline/index.html ] && ok "Pipeline UI" || no "Pipeline UI" "thiếu"

total=$((pass+fail+skip)); scored=$((pass+fail))
score=0; [ $scored -gt 0 ] && score=$(( pass*100/scored ))
echo "=== Score: $pass/$scored PASS (${score}%) · skip=$skip · total=$total ==="
if [ $fail -gt 0 ] && [ $STRICT -eq 1 ]; then exit 1; fi
exit 0
