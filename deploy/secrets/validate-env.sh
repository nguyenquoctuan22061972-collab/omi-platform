#!/usr/bin/env bash
# Validate env cho go-live (PRD-007 A). KHÔNG in giá trị secret — chỉ báo thiếu/đủ.
# Usage: set env (hoặc `set -a; . deploy/.env; set +a`) rồi: deploy/secrets/validate-env.sh
set -uo pipefail

# Nhóm bắt buộc để hệ thống lõi chạy.
REQUIRED_CORE=(AUTH_SECRET CRM_BASE N8N_BASE_URL)

# Nhóm theo adapter — chỉ bắt buộc nếu adapter đó được BẬT (<PREFIX>_ENABLED=true).
# format: "ENABLE_FLAG:VAR1,VAR2,..."
ADAPTER_GROUPS=(
  "TELEGRAM_ENABLED:TELEGRAM_BOT_TOKEN,TELEGRAM_CHAT_ID"
  "SMTP_ENABLED:SMTP_HOST,SMTP_PORT,SMTP_USER,SMTP_PASS"
  "ZALO_OA_ENABLED:ZALO_OA_ID,ZALO_OA_ACCESS_TOKEN"
  "FB_PAGE_ENABLED:FB_PAGE_ID,FB_PAGE_ACCESS_TOKEN"
  "OPENAI_ENABLED:OPENAI_API_KEY,OPENAI_MODEL"
  "VERTEX_ENABLED:GCP_PROJECT,GCP_LOCATION,VERTEX_MODEL"
)

missing=()
truthy() { case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in 1|true|yes|on) return 0;; *) return 1;; esac; }

echo "== Core =="
for v in "${REQUIRED_CORE[@]}"; do
  if [ -z "${!v:-}" ]; then echo "  MISSING $v"; missing+=("$v"); else echo "  OK      $v"; fi
done

echo "== Adapters (chỉ kiểm khi *_ENABLED=true) =="
for group in "${ADAPTER_GROUPS[@]}"; do
  flag="${group%%:*}"; vars="${group#*:}"
  if truthy "${!flag:-}"; then
    echo "  [$flag=on]"
    IFS=',' read -ra keys <<< "$vars"
    for v in "${keys[@]}"; do
      if [ -z "${!v:-}" ]; then echo "    MISSING $v"; missing+=("$v"); else echo "    OK      $v"; fi
    done
  else
    echo "  [$flag=off] bỏ qua ($vars)"
  fi
done

echo "== Kết quả =="
if [ ${#missing[@]} -eq 0 ]; then RESULT="PASS"; else RESULT="FAIL"; fi

# --report [file]: sinh deploy/runtime-status.md (PRD-011 B). KHÔNG in giá trị secret.
if [ "${1:-}" = "--report" ]; then
  OUT="${2:-deploy/runtime-status.md}"
  {
    echo "# Runtime Status — OMI Platform"
    echo
    echo "> Sinh bởi \`deploy/secrets/validate-env.sh --report\`. KHÔNG chứa giá trị secret."
    echo
    echo "**Kết quả tổng:** $RESULT · $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "## Core"
    for v in "${REQUIRED_CORE[@]}"; do
      if [ -z "${!v:-}" ]; then echo "- ❌ $v — MISSING"; else echo "- ✅ $v — present"; fi
    done
    echo
    echo "## Adapters (bật khi *_ENABLED=true)"
    for group in "${ADAPTER_GROUPS[@]}"; do
      flag="${group%%:*}"; vars="${group#*:}"
      if truthy "${!flag:-}"; then
        echo "- [$flag=on]"
        IFS=',' read -ra keys <<< "$vars"
        for v in "${keys[@]}"; do
          if [ -z "${!v:-}" ]; then echo "  - ❌ $v — MISSING"; else echo "  - ✅ $v — present"; fi
        done
      else
        echo "- [$flag=off] bỏ qua"
      fi
    done
  } > "$OUT"
  echo "Đã ghi $OUT"
fi

if [ "$RESULT" = "PASS" ]; then
  echo "PASS — đủ env cho cấu hình hiện tại."; exit 0
else
  echo "FAIL — thiếu ${#missing[@]} biến: ${missing[*]}"; exit 1
fi
