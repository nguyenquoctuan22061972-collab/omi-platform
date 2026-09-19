# GO-LIVE DAY — OMI Platform (PRD-011 F)

Quy trình go-live 1 ngày. Không đổi business logic — chỉ cấu hình env + bật.

## 0. Tiền đề
- VPS có Docker + Docker Compose, domain trỏ DNS, mở port 80/443.
- Repo đã clone; `deploy/.env` tạo từ `deploy/.env.example` + `deploy/secrets/secrets-manifest.md`.

## 1. Nạp & kiểm env (fail-fast)
```bash
set -a; . deploy/.env; set +a
deploy/secrets/validate-env.sh --report deploy/runtime-status.md   # phải PASS
```
Thiếu biến → điền `deploy/.env` rồi chạy lại (KHÔNG hardcode trong repo).

## 2. Go-Live (1 lệnh)
```bash
bash deploy/go-live.sh <image_tag>
```
Tự: preflight (validate-env + compose config) → backup → deploy → healthcheck → smoke → auto-rollback nếu fail.

## 3. Xác minh runtime
```bash
scripts/production-ready.sh                       # Score
curl -s https://<domain>/api/health/gateway       # status: ready (CRM+n8n reachable)
BASE=https://<domain> deploy/scripts/healthcheck.sh
```

## 4. Bật automation (khi cần)
Theo `workflows/runtime/activation-checklist.md` (từng WF, chỉ khi env hợp lệ).

## 5. Theo dõi 24h đầu
Theo `FIRST_24H_MONITORING.md`. Sự cố → `ROLLBACK_GUIDE.md`.

## Definition of Done
- validate-env PASS · go-live.sh OK · /health/gateway ready · healthcheck xanh · CI xanh.
