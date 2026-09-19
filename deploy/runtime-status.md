# Runtime Status — OMI Platform

> **Template.** Regenerate trên VPS bằng:
> `set -a; . deploy/.env; set +a; deploy/secrets/validate-env.sh --report deploy/runtime-status.md`
> File KHÔNG chứa giá trị secret — chỉ present/MISSING.

**Kết quả tổng:** FAIL (chưa nạp `deploy/.env` — trạng thái mặc định của template)

## Core
- ❌ AUTH_SECRET — MISSING
- ❌ CRM_BASE — MISSING
- ❌ N8N_BASE_URL — MISSING

## Adapters (bật khi *_ENABLED=true)
- [TELEGRAM_ENABLED=off] bỏ qua
- [SMTP_ENABLED=off] bỏ qua
- [ZALO_OA_ENABLED=off] bỏ qua
- [FB_PAGE_ENABLED=off] bỏ qua
- [OPENAI_ENABLED=off] bỏ qua
- [VERTEX_ENABLED=off] bỏ qua
