# API Specification — Auth & RBAC (PRD-002)

Base URL: `http://<host>:8081` · `application/json`. Khớp `apps/auth-rbac/src/api.py`.

Auth: gửi access token qua header `Authorization: Bearer <jwt>`.

---

## POST /auth/login
Request: `{ "username": "admin", "password": "secret" }`
- `200`: `{ "access_token": "...", "refresh_token": "...", "token_type": "Bearer", "expires_in": 900 }`
- `401`: `{ "error": "invalid credentials" }` (ghi audit `login_failed`)

## POST /auth/refresh
Request: `{ "refresh_token": "..." }`
- `200`: `{ "access_token": "...", "expires_in": 900 }` (audit `refresh`)
- `401`: refresh token sai/đã thu hồi

## POST /auth/logout
Header: `Authorization: Bearer <access>` · Request: `{ "refresh_token": "..." }`
- `200`: `{ "ok": true }` (thu hồi refresh; audit `logout`)

## GET /auth/me
Header: `Authorization: Bearer <access>`
- `200`: `{ "id": "...", "username": "...", "roles": ["Admin"], "permissions": [...] }`
- `401`: token thiếu/sai/hết hạn

## GET /contacts  (endpoint demo có RBAC)
Yêu cầu permission `contact:read`.
- `200`: `{ "data": [...] }`
- `401`: chưa xác thực · `403`: `{ "error": "forbidden" }` (audit `access_denied`)

---

## Mã trạng thái
| Tình huống | Mã |
|---|---|
| OK | 200 |
| Chưa xác thực / token sai/hết hạn | 401 |
| Không đủ quyền (RBAC) | 403 |

## Ma trận quyền (rbac/matrix.py)
| Permission | Admin | Manager | Operator | Viewer |
|---|:--:|:--:|:--:|:--:|
| contact:read | ✅ | ✅ | ✅ | ✅ |
| contact:write | ✅ | ✅ | ✅ | ❌ |
| pipeline:write | ✅ | ✅ | ✅ | ❌ |
| audit:read | ✅ | ✅ | ❌ | ❌ |
| user:manage | ✅ | ❌ | ❌ | ❌ |
