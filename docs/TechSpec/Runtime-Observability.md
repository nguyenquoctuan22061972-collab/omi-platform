# Tech Spec — Runtime Integration & Observability (PRD-008)

**PRD:** [`../PRD/PRD-008.md`](../PRD/PRD-008.md) · Additive; giữ ADR/naming.

## 1. Nguyên tắc
Python stdlib, mock/abstraction, không network/không secret. Mỗi thành phần độc lập,
không sửa module hiện có (import thêm, không thay thế).

## 2. Runtime Health (A)
`apps/runtime-health` (http.server, cổng 8082). Endpoint MỚI: `/health`, `/health/live`,
`/health/ready` (503 khi not_ready), `/version`, `/build-info`. Dependency status suy từ
env (`CRM_BASE`/`AUTH_SECRET`/`N8N_BASE_URL`) — không gọi service thật.

## 3. Logging (B)
`libs/logging` — `JsonFormatter`, `get_logger` (propagate=False → **không đụng logger cũ**),
`new_request_id/new_correlation_id`, `audit_event`, `rotation_config`.

## 4. Audit (C)
`libs/audit` — `AuditTrail` + `Sink` (MemorySink mặc định), 6 loại event, **redact** khoá
nghi secret. File/DB sink cắm sau (giữ interface).

## 5. Metrics (D)
`libs/metrics` — `MetricsRegistry` + `Provider` (MockProvider). `render_prometheus` trả text
exposition (KHÔNG push Prometheus). 5 metric chuẩn.

## 6. Backup Verify (F)
`deploy/backup/` — `backup-verify.sh` (gzip/tar + sha256 sidecar), `restore-verify.sh`
(dry-run vào thư mục tạm, không đụng ./data), `retention-policy.md`. Không ghi đè
`deploy/scripts/backup.sh`.

## 7. n8n Runtime Validation (G)
`workflows/runtime/validate.py` — đọc workflow.json (webhook/credential/disabled/activation).
Chỉ đọc, không sửa workflow.

## 8. Docs (E,H)
alert-policy.md, CEO-Live-Dashboard.md — additive, không sửa doc/KPI hiện có.

## 9. QA/CI
Test suites mới thêm vào CI (runtime-health, libs/logging|audit|metrics); workflows step tự
chạy test_runtime; deploy step tự chạy test_backup_verify. Regression giữ nguyên → CI xanh.
