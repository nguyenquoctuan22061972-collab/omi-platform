# WF050 — Dashboard KPI Sync (n8n) · PLACEHOLDER

**Trạng thái:** 🟡 Placeholder — chưa nối credential/deploy.
**Map PRD-001 §9:** bước 5 (Dashboard cập nhật).

## Luồng n8n (dự kiến)
```
[Cron / hoặc realtime trigger]
   → [HTTP Request: đọc KPI từ CRM Core]   (dashboard.kpi — realtime §10)
   → [Function: format số liệu]
   → [Cập nhật Dashboard / gửi báo cáo định kỳ]
```

## Ghi chú
- KPI đọc realtime từ DB (không cache) — bám PRD §10.
- Nếu chỉ cần realtime trên UI thì dashboard gọi trực tiếp CRM Core; WF050 dùng cho
  báo cáo định kỳ/tổng hợp ngoài giờ.

Xem `workflow.json` (skeleton placeholder).
