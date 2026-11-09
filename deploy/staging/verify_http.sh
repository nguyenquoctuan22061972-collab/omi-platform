#!/usr/bin/env bash
# AFFOS staging RUNTIME verifier (Milestone 2, TASK 3). Run ON the staging host against the running
# affos-runtime. DRY-RUN: makes NO paid provider call and NO live affiliate call. PASS/FAIL per check;
# exit 0 iff all PASS. No secret is printed.
#
#   BASE_URL=http://localhost:8099 deploy/staging/verify_http.sh
#
# Covers: liveness (/health), readiness (/ready, DB-aware), JWT-required (401), and the DB-down → 503
# contract (readiness flips to 503 and ingest refuses — never a false success — when Postgres is down).
set -uo pipefail
BASE="${BASE_URL:-http://localhost:8099}"
pass=0; fail=0
ck(){ local name="$1" want="$2" got="$3"; if [ "$got" = "$want" ]; then echo "[PASS] $name (HTTP $got)"; pass=$((pass+1)); else echo "[FAIL] $name (want $want, got $got)"; fail=$((fail+1)); fi; }
code(){ curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$@" 2>/dev/null || echo 000; }

echo "== affos-runtime @ $BASE =="
ck "liveness /health 200"            200 "$(code "$BASE/health")"
ck "liveness /healthz 200"           200 "$(code "$BASE/healthz")"
ck "readiness /ready 200 (DB up)"    200 "$(code "$BASE/ready")"
# JWT enforced: an UNAUTHENTICATED write must be rejected (401), never processed.
ck "ingest requires auth -> 401"     401 "$(code -X POST "$BASE/affos/revenue/ingest" -H 'Content-Type: application/json' --data '{}')"

cat <<'NOTE'

-- Operator-driven negative checks (run with Postgres intentionally stopped) --
  # Stop staging Postgres (e.g. `docker compose -f deploy/docker-compose.staging.yml stop postgres`), then:
  #   GET  /ready                      -> EXPECT 503 (readiness detects DB down; liveness /health stays 200)
  #   POST /affos/revenue/ingest (authed) -> EXPECT 503 "store unavailable" (NO false success, no SQLite downgrade)
  # Restart Postgres -> /ready returns 200 within AFFOS_DB_CONNECT_ATTEMPTS (mid-life reconnect).
NOTE
echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
