# Auth & RBAC (PRD-002)

Xác thực (JWT + refresh + bcrypt) và phân quyền RBAC cho OMI Platform.

- PRD: [`../../docs/PRD/PRD-002.md`](../../docs/PRD/PRD-002.md)
- TechSpec: [`../../docs/TechSpec/Auth-RBAC.md`](../../docs/TechSpec/Auth-RBAC.md)
- DB: [`../../docs/Database/Auth-RBAC-schema.md`](../../docs/Database/Auth-RBAC-schema.md)
- API: [`../../docs/API/Auth-RBAC-api.md`](../../docs/API/Auth-RBAC-api.md)

## Phụ thuộc
```bash
pip install -r apps/auth-rbac/requirements.txt   # bcrypt
```
JWT dùng stdlib (HS256), không cần thư viện ngoài.

## Chạy
```bash
AUTH_SECRET=$(openssl rand -hex 32) python3 apps/auth-rbac/run.py   # cổng 8081
```

## API
`POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `GET /auth/me`
· `GET /contacts` (demo RBAC, cần `contact:read`).

## QA
```bash
cd apps/auth-rbac && AUTH_SECRET=test python3 -m unittest discover -s tests -p 'test_*.py' -v
```
6 nhóm QA theo PRD §6. Xem [`../../docs/QA/Auth-RBAC-checklist.md`](../../docs/QA/Auth-RBAC-checklist.md).

## Cấu trúc
```
apps/auth-rbac/
├── run.py  requirements.txt
├── src/
│   ├── api.py
│   ├── auth/{db,passwords,jwt_util,tokens,audit,service}.py
│   └── rbac/{matrix,middleware}.py
└── tests/{_base,test_login,test_token,test_rbac,test_audit}.py
```

## Giới hạn MVP
Refresh store trong SQLite (dev) → chuyển Redis/DB bền ở Deployment. Bắt buộc đặt
`AUTH_SECRET` mạnh ở production.
