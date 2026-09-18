# QA Checklist — Runtime Integration & Observability (PRD-008)

## Kết quả (CI-mirror, cục bộ)
| Suite | KQ |
|---|---|
| apps/runtime-health (A) | ✅ PASS |
| libs/logging (B) | ✅ PASS |
| libs/audit (C) | ✅ PASS |
| libs/metrics (D) | ✅ PASS |
| workflows incl runtime (G) | ✅ PASS |
| deploy incl backup-verify (F) | ✅ PASS |
| Regression: crm-core / auth-rbac / dashboard / integrations | ✅ PASS |
| py_compile toàn bộ module mới | ✅ PASS |

## Map module → QA
- A: `apps/runtime-health/tests/test_health.py` (unit + HTTP smoke, ready/live/version/build/404)
- B: `libs/logging/tests/test_logging.py` (json, ids, isolated logger, rotation)
- C: `libs/audit/tests/test_audit.py` (6 event, redact secret, invalid raise)
- D: `libs/metrics/tests/test_metrics.py` (5 metric, provider, prometheus text)
- F: `deploy/tests/test_backup_verify.py` (**backup dry-run thực tế** + checksum + corrupt fail)
- G: `workflows/tests/test_runtime.py` (webhook/credential/disabled/activation)
- E,H: docs review

## Acceptance
- [x] Additive; không đổi PRD-001..007, ADR, capability-map, naming, business logic
- [x] Không thay endpoint cũ; không sửa logger cũ; không gọi Prometheus/API thật
- [x] Không ghi secret (audit redact; log không secret)
- [x] Backup verify không ghi đè script cũ; restore-verify dry-run không đụng ./data
- [x] CI thêm 4 step (runtime-health, logging, audit, metrics) — xanh

## Chạy
```bash
for d in apps/runtime-health libs/logging libs/audit libs/metrics workflows deploy; do
  ( cd $d && python3 -m unittest discover -s tests -p 'test_*.py' ); done
python3 workflows/runtime/validate.py   # activation report
scripts/production-ready.sh             # readiness score
```
