# QA Checklist — Auth & RBAC (PRD-002)

## Kết quả
- ✅ **19/19 unit test PASS** (`apps/auth-rbac/tests/`)
- ✅ **Smoke test HTTP PASS** (login, /auth/me, refresh, logout, RBAC, 401)

## Map QA PRD §6 → test
| QA PRD | Test | Kết quả |
|---|---|---|
| Login PASS | `test_login.test_login_success` | ✅ |
| Login sai PASS | `test_login.test_login_wrong_password/unknown_user` | ✅ |
| Token hết hạn PASS | `test_token.test_expired_token_rejected` | ✅ |
| Refresh PASS | `test_token.test_refresh_issues_new_access` | ✅ |
| RBAC PASS | `test_rbac.*` (allow/deny theo role) | ✅ |
| Audit Log PASS | `test_audit.*` (login/failed/refresh/logout) | ✅ |

## Chức năng bắt buộc (PRD §3) — trạng thái
- [x] JWT Access Token (HS256, stdlib)
- [x] Refresh Token (issue/resolve/revoke)
- [x] Password Hash (bcrypt thật, prefix `$2`)
- [x] Login / Logout / Refresh / `/auth/me`
- [x] RBAC Middleware (`require_permission` → 401/403)
- [x] Audit Log (login_success/login_failed/refresh/logout/access_denied)

## Database (PRD §5) — đúng 5 bảng
- [x] users / roles / permissions / user_roles / audit_logs
- [x] Seed 4 roles + permission catalog

## Bảo mật
- [x] Mật khẩu chỉ lưu bcrypt hash
- [x] JWT verify chữ ký + `exp`; token giả/hết hạn bị từ chối
- [ ] AUTH_SECRET mạnh + refresh store bền (Redis/DB) — giai đoạn Deployment

## Lệnh chạy lại
```bash
cd apps/auth-rbac && pip install -r requirements.txt
AUTH_SECRET=test python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Định nghĩa Done — đạt
File ✅ · Checklist ✅ · Test ✅ · Risk notes ✅
