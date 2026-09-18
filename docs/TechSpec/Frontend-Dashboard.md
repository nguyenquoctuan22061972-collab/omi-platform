# Tech Spec — Frontend Dashboard

**PRD:** [`../PRD/PRD-004.md`](../PRD/PRD-004.md) · **Dùng:** CR-001 `GET /dashboard/kpi`
**Liên quan:** [`Architecture/Frontend-Dashboard-flows.md`](../Architecture/Frontend-Dashboard-flows.md)

## 1. Stack & lý do
Vanilla JS (ES modules) + HTML + CSS, **không build, không npm** → chạy offline, nhất
quán ADR stdlib-first. Không thêm dependency (không redesign kiến trúc dự án).

## 2. Folder (`apps/dashboard/`)
```
index.html · config.example.js · styles.css · mock/kpi.json
src/app.js (bootstrap) · src/router.js · src/store.js · src/api.js
src/components/{nav,kpiCards,pipelineChart,overview}.js
tests/test_dashboard.py (validator TC1-TC10)
```

## 3. Component map
| Component | Trách nhiệm | Nguồn dữ liệu |
|---|---|---|
| nav | thanh điều hướng + responsive toggle | route hiện tại |
| overview | layout màn Dashboard | store.kpi |
| kpiCards | 3 thẻ: contacts, messages, win rate | store.kpi |
| pipelineChart | bar theo 6 stage | store.kpi.pipeline_by_stage |

## 4. Routing (hash-based)
| Hash | Màn | Trạng thái |
|---|---|---|
| `#/` `#/overview` | Dashboard (KPI) | đầy đủ |
| `#/contacts` `#/inbox` `#/pipeline` | skeleton (theo wireframe §8) | placeholder |

Router: parse `location.hash` → chọn view → mount vào `#app`. Fallback `#/overview`.

## 5. State management
`store.js`: `{ state, get(), set(patch), subscribe(fn) }` — pub/sub tối giản. KPI lưu
trong store; component subscribe → re-render khi đổi.

## 6. Integration layer (`api.js`)
- `getKpi()`: `fetch(`${CRM_BASE}/dashboard/kpi`)` với timeout; lỗi/không cấu hình →
  trả mock (`mock/kpi.json`) + cờ `degraded`.
- `CRM_BASE` đọc từ `window.OMI_CONFIG?.CRM_BASE` (file `config.js`, mẫu
  `config.example.js`). Không hardcode host.

## 7. Error handling / retry / logging
- **Error:** fetch fail/timeout/non-200 → dùng mock, set `store.error` → UI hiện banner
  "dữ liệu tạm (mock)".
- **Retry:** `getKpi` thử lại tối đa 2 lần, backoff 500ms→1500ms trước khi fallback mock.
- **Logging:** `console.warn` khi degraded/retry; `console.error` khi fail hẳn. Không log secret.
- **Polling:** refresh mỗi `POLL_MS` (mặc định 30s), có thể tắt.

## 8. Sequence & data-flow
Xem `Architecture/Frontend-Dashboard-flows.md`.

## 9. QA
`tests/test_dashboard.py` validator tĩnh TC1-TC10 (chạy bằng python, offline) +
`docs/QA/Frontend-Dashboard-checklist.md`.

## 10. Không phá vỡ
Chỉ thêm `apps/dashboard/`; không sửa CRM Core (ngoài CR-001), Auth, Automation.
