# Database Schema — Auth & RBAC (PRD-002 §5)

Khớp 1-1 với `apps/auth-rbac/src/auth/db.py`. Đúng 5 bảng PRD.

## ERD (text)
```
users 1 ──< user_roles >── 1 roles
users 1 ──< audit_logs
permissions : catalog (role→permission map trong rbac/matrix.py)
```

## DDL (SQLite)
```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,      -- uuid4
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,         -- bcrypt
    created_at    TEXT NOT NULL
);
CREATE TABLE roles (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE            -- Admin/Manager/Operator/Viewer
);
CREATE TABLE permissions (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE            -- vd: contact:read, contact:write...
);
CREATE TABLE user_roles (
    user_id TEXT NOT NULL REFERENCES users(id),
    role_id INTEGER NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
CREATE TABLE audit_logs (
    id        TEXT PRIMARY KEY,          -- uuid4
    user_id   TEXT,                      -- có thể NULL (login_failed)
    action    TEXT NOT NULL,             -- login_success/login_failed/logout/refresh/access_denied
    detail    TEXT DEFAULT '',
    timestamp TEXT NOT NULL
);
```

## Seed mặc định
- **roles:** Admin, Manager, Operator, Viewer.
- **permissions:** catalog gom từ `rbac/matrix.py` (vd `contact:read`, `contact:write`,
  `pipeline:write`, `user:manage`, `audit:read`).

## Ghi chú thiết kế
- Không thêm bảng `role_permissions` (ngoài 5 bảng PRD): 4 role cố định → ánh xạ giữ
  ở code `rbac/matrix.py`; `permissions` là catalog để kiểm tra tên quyền hợp lệ.
- `PRAGMA foreign_keys = ON`.
