#!/usr/bin/env bash
# Post-deploy: healthcheck + smoke test (PRD-007 D). Exit 0 = OK.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

BASE="${BASE:-http://localhost}"
fail=0
log() { echo "[post-deploy] $*"; }

# 1. Healthcheck (dùng script sẵn có)
if BASE="$BASE" bash deploy/scripts/healthcheck.sh; then log "healthcheck OK"; else log "healthcheck FAIL"; fail=1; fi

# 2. Smoke test: KPI trả JSON có trường bắt buộc
kpi="$(curl -sk --max-time 8 "$BASE/api/crm/dashboard/kpi" || true)"
if echo "$kpi" | grep -q '"total_contacts"' && echo "$kpi" | grep -q '"win_rate"'; then
  log "smoke KPI OK"
else
  log "smoke KPI FAIL"; fail=1
fi

# 3. Dashboard tĩnh phục vụ được
code="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 8 "$BASE/" || echo 000)"
echo "$code" | grep -qE '200|301' && log "dashboard OK ($code)" || { log "dashboard FAIL ($code)"; fail=1; }

[ $fail -eq 0 ] && { log "POST-DEPLOY PASS"; exit 0; } || { log "POST-DEPLOY FAIL"; exit 1; }
