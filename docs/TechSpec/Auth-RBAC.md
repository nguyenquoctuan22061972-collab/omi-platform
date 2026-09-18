# Tech Spec — Auth & RBAC

**Tên Module:** Auth & RBAC
**PRD tham chiếu:** [`../PRD/PRD-002.md`](../PRD/PRD-002.md)

## Kiến trúc tổng quan
Python 3.11. `sqlite3` (DB), `http.server` (REST), `unittest` (QA). Phụ thuộc ngoài
**duy nhất: `bcrypt`** (PRD yêu cầu). JWT hiện thực bằng **stdlib HS256** (hmac +
hashlib + base64) — JWT là định dạng, không ràng buộc thư viện.

```
Client → api → auth.service ──> passwords(bcrypt)
                    │            jwt_util(HS256)  tokens(refresh store)
                    │            audit(audit_logs)
                    └─ rbac.middleware ─> rbac.matrix (role→permission)
                                   (users/roles/permissions/user_roles/audit_logs)
```

## Thành phần & trách nhiệm (map module code)
| Module | File | Trách nhiệm |
|---|---|---|
| auth-db | `src/auth/db.py` | Schema 5 bảng + seed roles/permissions |
| passwords | `src/auth/passwords.py` | bcrypt hash & verify |
| jwt | `src/auth/jwt_util.py` | HS256 encode/decode + kiểm tra `exp` |
| tokens | `src/auth/tokens.py` | Lưu/thu hồi refresh token (logout) |
| audit | `src/auth/audit.py` | Ghi `audit_logs` |
| service | `src/auth/service.py` | register/login/logout/refresh/me |
| rbac-matrix | `src/rbac/matrix.py` | Ma trận role→permission (4 role cố định) |
| rbac-mw | `src/rbac/middleware.py` | `require_permission`, kiểm tra từ access token |
| api | `src/api.py` | `/auth/*` + endpoint demo có RBAC |

## Mô hình dữ liệu (PRD §5 — đúng 5 bảng)
- **users**(id, username, password_hash, created_at)
- **roles**(id, name)  — Admin/Manager/Operator/Viewer
- **permissions**(id, name)  — catalog quyền
- **user_roles**(user_id, role_id)
- **audit_logs**(id, user_id, action, detail, timestamp)

> Ánh xạ **role→permission** giữ trong `rbac/matrix.py` (4 role cố định, không cần
> bảng join ngoài 5 bảng PRD). `permissions` là catalog để validate tên quyền.

## Token
- **Access token (JWT HS256):** claims `sub`, `username`, `roles`, `iat`, `exp`
  (mặc định 15 phút). Ký bằng `AUTH_SECRET` (env).
- **Refresh token:** chuỗi ngẫu nhiên (`secrets.token_urlsafe`), lưu hash trong
  bộ nhớ/DB store; `refresh` cấp access mới; `logout` thu hồi.

## RBAC
Ma trận quyền (Admin ⊇ Manager ⊇ Operator ⊇ Viewer). `require_permission(perm)`
đọc roles từ access token → hợp permissions → cho/từ chối (403).

## Audit Log
Ghi mọi sự kiện: `login_success`, `login_failed`, `logout`, `refresh`,
`access_denied`. Có `user_id` (nếu biết), `action`, `detail`, `timestamp`.

## Bảo mật
- Mật khẩu chỉ lưu bcrypt hash.
- JWT verify chữ ký + `exp` (chống token giả/hết hạn).
- Secret qua env, không commit.

## Chiến lược kiểm thử (map PRD §6)
| QA | File |
|---|---|
| Login PASS / Login sai PASS | `tests/test_login.py` |
| Token hết hạn / Refresh | `tests/test_token.py` |
| RBAC PASS | `tests/test_rbac.py` |
| Audit Log PASS | `tests/test_audit.py` |

## Rủi ro
- Secret yếu → bắt buộc set `AUTH_SECRET` mạnh ở Deployment.
- Refresh store in-memory ở MVP → chuyển persistent (Redis/DB) khi deploy.
