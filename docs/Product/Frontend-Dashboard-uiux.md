# UI/UX — Frontend Dashboard (PRD-004)

## 1. Wireframe Desktop
```
+---------------------------------------------------------------+
| OMI ▸ [Dashboard] Contacts Inbox Pipeline           [degraded]|
+---------------------------------------------------------------+
| ┌ Contacts ┐  ┌ Messages ┐  ┌ Win rate ┐                      |
| │  1,240   │  │  8,930   │  │   27%    │                      |
| └──────────┘  └──────────┘  └──────────┘                      |
| Pipeline theo stage                                           |
| lead ▓▓▓▓  contacted ▓▓▓  qualified ▓▓  proposal ▓  won ▓ lost ▓|
+---------------------------------------------------------------+
```

## 2. Wireframe Mobile (≤640px)
```
+-----------------------------+
| ☰  OMI Dashboard            |
+-----------------------------+
| ┌ Contacts ┐                |
| │  1,240   │                |
| └──────────┘                |
| ┌ Messages ┐                |
| │  8,930   │                |
| └──────────┘                |
| ┌ Win rate ┐                |
| │   27%    │                |
| └──────────┘                |
| Pipeline (bar dọc/cuộn)     |
+-----------------------------+
```

## 3. Component map
`nav` · `overview` (layout) · `kpiCards` (3 thẻ) · `pipelineChart` (bar 6 stage).

## 4. Routing
`#/` `#/overview` → Dashboard · `#/contacts` `#/inbox` `#/pipeline` → skeleton (§8 PRD-001).

## 5. State
`store`: `{ kpi, degraded, error, route }`. Component subscribe → re-render.

## 6. Nguyên tắc UX
- Không trắng màn khi lỗi: hiện mock + banner "dữ liệu tạm".
- Loading skeleton khi fetch lần đầu.
- Accessible: contrast đủ, nav bàn phím, aria-label trên thẻ KPI.
- Responsive breakpoint 640px.

## 7. Màu/định dạng
Trung tính, KPI nổi bật; bar pipeline dùng 1 hệ màu tuần tự (không phụ thuộc thư viện).
