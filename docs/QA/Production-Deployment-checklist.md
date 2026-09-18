# QA Checklist — Production Deployment (PRD-005)

## Kết quả
- ✅ **15/15 validator test PASS** (`deploy/tests/test_deploy.py`)
- ✅ Toàn bộ 5 test-suite PASS (CI mirror): crm-core, auth-rbac, workflows, dashboard, deploy

## TC1-TC15 → Acceptance
| TC | Nội dung | Test | KQ |
|---|---|---|---|
| TC1 | Compose có đủ service | `test_TC1_compose_services` | ✅ |
| TC2 | Dockerfile mỗi app service | `test_TC2_dockerfiles_exist` | ✅ |
| TC3 | Container non-root | `test_TC3_dockerfiles_non_root` | ✅ |
| TC4 | Rate limit (nginx) | `test_TC4_rate_limit` | ✅ |
| TC5 | SSL (listen 443 + cert) | `test_TC5_ssl` | ✅ |
| TC6 | CSP | `test_TC6_csp` | ✅ |
| TC7 | Security headers (HSTS/XFO/XCTO/Referrer) | `test_TC7_security_headers` | ✅ |
| TC8 | CORS | `test_TC8_cors` | ✅ |
| TC9 | Reverse proxy /api/crm + /api/auth | `test_TC9_reverse_proxy` | ✅ |
| TC10 | CI chạy test mọi module | `test_TC10_ci_runs_tests` | ✅ |
| TC11 | Deploy thủ công + environment | `test_TC11_deploy_manual` | ✅ |
| TC12 | .env.example không secret thật | `test_TC12_env_example_no_secret` | ✅ |
| TC13 | backup/restore/healthcheck script | `test_TC13_backup_restore_health` | ✅ |
| TC14 | healthcheck + restart policy | `test_TC14_healthcheck_and_restart` | ✅ |
| TC15 | Không secret hardcode | `test_TC15_no_hardcoded_secret` | ✅ |

## Acceptance criteria (Definition of Done)
- [x] PRD-005 + TechSpec
- [x] Docker Compose production + Dockerfile (non-root, healthcheck)
- [x] Nginx reverse proxy + SSL + rate limit + CORS + CSP + security headers
- [x] CI/CD (build/test tự động; deploy thủ công có approval)
- [x] Secrets: `.env.example` (không secret), `.env` gitignored
- [x] Backup/Restore + Healthcheck script
- [x] Monitoring/Logging/Alerting (runbook) + Rollback strategy
- [x] Production checklist + Runbook + Disaster Recovery
- [x] Security hardening doc
- [x] 15/15 TC PASS; CI mirror xanh
- [x] Không phá PRD-001..004

## Chạy
```bash
cd deploy && python3 -m unittest discover -s tests -p 'test_*.py' -v
# Kiểm tra compose đầy đủ (khi có docker): docker compose -f deploy/docker-compose.prod.yml config
```
