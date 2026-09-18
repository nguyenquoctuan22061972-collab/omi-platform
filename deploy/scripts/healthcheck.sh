#!/usr/bin/env bash
# Healthcheck endpoints (PRD-005 §7). Usage: BASE=https://omi.example.com deploy/scripts/healthcheck.sh
set -euo pipefail

BASE="${BASE:-http://localhost}"
fail=0

check() {
  local name="$1" url="$2" expect="$3"
  code="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 8 "$url" || echo 000)"
  if echo "$expect" | grep -qw "$code"; then
    echo "OK   $name ($code)"
  else
    echo "FAIL $name ($code, expect $expect)"; fail=1
  fi
}

check "CRM KPI"  "$BASE/api/crm/dashboard/kpi" "200"
check "Auth me"  "$BASE/api/auth/auth/me"      "200 401"
check "Dashboard" "$BASE/"                      "200 301"

exit $fail
