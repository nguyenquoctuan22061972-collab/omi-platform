# Frontend Dashboard (PRD-004)

Dashboard quản trị OMI Platform. Vanilla JS (ES modules), không build/không npm.

- PRD: [`../../docs/PRD/PRD-004.md`](../../docs/PRD/PRD-004.md)
- TechSpec: [`../../docs/TechSpec/Frontend-Dashboard.md`](../../docs/TechSpec/Frontend-Dashboard.md)
- UI/UX: [`../../docs/Product/Frontend-Dashboard-uiux.md`](../../docs/Product/Frontend-Dashboard-uiux.md)

## Chạy
```bash
cp apps/dashboard/config.example.js apps/dashboard/config.js   # đặt CRM_BASE
cd apps/dashboard && python3 -m http.server 8000               # mở http://localhost:8000
```
Chưa cấu hình `CRM_BASE` hoặc CRM lỗi → app tự dùng `mock/kpi.json` + banner "degraded".

## Tích hợp
`GET {CRM_BASE}/dashboard/kpi` (CR-001). Retry x2 + mock fallback (TechSpec §7).

## Cấu trúc
```
index.html · config.example.js · styles.css · mock/kpi.json
src/{app,router,store,api}.js · src/components/{nav,kpiCards,pipelineChart,overview}.js
tests/test_dashboard.py
```

## QA
```bash
cd apps/dashboard && python3 -m unittest discover -s tests -p 'test_*.py' -v
```
Validator TC1-TC10. Xem `../../docs/QA/Frontend-Dashboard-checklist.md`.

## Responsive
Desktop: grid 3 cột. Mobile ≤640px: 1 cột + nav hamburger.
