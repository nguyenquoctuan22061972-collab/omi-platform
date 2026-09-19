#!/usr/bin/env bash
# Detect runtime & prepare deployment env (PRD-011/12 handoff). ADDITIVE, READ-ONLY detect.
# KHÔNG cài lại Docker/Compose/PostgreSQL/n8n. Chỉ SINH env còn thiếu; không ghi đè giá trị có sẵn.
# Chạy trên VPS: cd /opt/omi-platform && bash deploy/detect-and-prepare-env.sh
set -uo pipefail
cd "$(dirname "$0")/.." 2>/dev/null || true

ENV_FILE="deploy/.env"
log() { echo "[detect] $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# ---- ensure_env KEY VALUE : chỉ thêm nếu KEY chưa có (generate missing only) ----
ensure_env() {
  local key="$1" val="$2"
  touch "$ENV_FILE"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    log "giữ nguyên $key (đã có)"; return 0
  fi
  if [ -z "$val" ]; then
    log "THIẾU $key (không tự dò được — cần nhập tay)"; return 1
  fi
  printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  # Không in giá trị secret
  case "$key" in AUTH_SECRET|*TOKEN*|*SECRET*|*PASS*) log "đã sinh $key (giá trị ẩn)";;
    *) log "đã đặt $key=$val";; esac
}

# ---- 1. Detect runtime (read-only) ----
log "== Runtime =="
have docker && log "docker: $(docker --version 2>/dev/null)" || log "docker: KHÔNG thấy"
docker compose version >/dev/null 2>&1 && log "compose: $(docker compose version --short 2>/dev/null)" || true
RUNNING="$(docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' 2>/dev/null)"
[ -n "$RUNNING" ] && { log "containers đang chạy:"; echo "$RUNNING" | sed 's/^/    /'; } || log "không liệt kê được container"

# ---- 3. AUTH_SECRET (64 hex chars) ----
AUTH_SECRET_VAL=""
if have openssl; then AUTH_SECRET_VAL="$(openssl rand -hex 32)"; fi
ensure_env "AUTH_SECRET" "$AUTH_SECRET_VAL"

# ---- 4. Detect CRM_BASE ----
# Ưu tiên container crm-core đang chạy; nếu chưa (go-live sẽ dựng) → service nội bộ compose.
CRM_BASE_VAL=""
CRM_CT="$(docker ps --filter 'name=crm-core' --format '{{.Names}}' 2>/dev/null | head -1)"
if [ -n "$CRM_CT" ]; then
  PORT="$(docker inspect --format '{{range $p,$c := .NetworkSettings.Ports}}{{if $c}}{{(index $c 0).HostPort}}{{end}}{{end}}' "$CRM_CT" 2>/dev/null | head -1)"
  [ -n "$PORT" ] && CRM_BASE_VAL="http://localhost:${PORT}" || CRM_BASE_VAL="http://crm-core:8080"
else
  # crm-core sẽ do go-live compose dựng trong network 'omi' → dùng service DNS nội bộ.
  CRM_BASE_VAL="http://crm-core:8080"
fi
ensure_env "CRM_BASE" "$CRM_BASE_VAL"

# ---- 5. Detect N8N_BASE_URL từ container n8n đang chạy ----
N8N_VAL=""
N8N_CT="$(docker ps --filter 'name=n8n' --format '{{.Names}}' 2>/dev/null | head -1)"
if [ -n "$N8N_CT" ]; then
  # thử env editor/webhook trong container
  for k in N8N_EDITOR_BASE_URL WEBHOOK_URL N8N_HOST; do
    v="$(docker inspect --format "{{range .Config.Env}}{{println .}}{{end}}" "$N8N_CT" 2>/dev/null | grep -E "^${k}=" | head -1 | cut -d= -f2-)"
    if [ -n "$v" ]; then
      case "$k" in N8N_HOST) N8N_VAL="https://${v}";; *) N8N_VAL="$v";; esac
      break
    fi
  done
  # fallback: published port 5678
  if [ -z "$N8N_VAL" ]; then
    HP="$(docker inspect --format '{{range $p,$c := .NetworkSettings.Ports}}{{if eq $p "5678/tcp"}}{{(index $c 0).HostPort}}{{end}}{{end}}' "$N8N_CT" 2>/dev/null | head -1)"
    [ -n "$HP" ] && N8N_VAL="http://localhost:${HP}"
  fi
fi
ensure_env "N8N_BASE_URL" "$N8N_VAL"

# ---- 2. Sinh các key khung còn thiếu (không giá trị thật) ----
grep -qE '^OMI_DOMAIN=' "$ENV_FILE" || echo '# OMI_DOMAIN=your-domain.com   # nhập tay nếu dùng SSL' >> "$ENV_FILE"
grep -qE '^LETSENCRYPT_EMAIL=' "$ENV_FILE" || echo '# LETSENCRYPT_EMAIL=admin@your-domain.com' >> "$ENV_FILE"

# ---- 6. Validate ----
log "== Validate =="
set -a; . "$ENV_FILE" 2>/dev/null; set +a
if bash deploy/secrets/validate-env.sh --report deploy/runtime-status.md; then
  echo
  echo "RESULT: PASS ✅"
  echo "== 7. Go-Live command =="
  echo "  bash deploy/go-live.sh latest"
  exit 0
else
  echo
  echo "RESULT: FAIL ❌"
  echo "== 8. Biến còn THIẾU (cần nhập tay vào deploy/.env) =="
  for v in AUTH_SECRET CRM_BASE N8N_BASE_URL; do
    val="$(grep -E "^${v}=" "$ENV_FILE" | cut -d= -f2-)"
    [ -z "$val" ] && echo "  - $v (chưa dò được — nhập tay)"
  done
  echo "  (Adapter *_ENABLED=true nào bật thì thêm credential tương ứng — xem deploy/secrets/secrets-manifest.md)"
  exit 1
fi
