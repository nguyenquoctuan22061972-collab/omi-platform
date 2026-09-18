# CR-001 — CRM Core: thêm `GET /dashboard/kpi`

- **Trạng thái:** Implemented
- **Ngày:** 2026-09-18
- **Module ảnh hưởng:** CRM Core (PRD-001)
- **Liên quan:** PRD-003 §11 (gap WF050), PRD-004 (Frontend Dashboard)

## 1. Lý do
WF050 (Automation) và Frontend Dashboard cần đọc KPI qua HTTP. Hàm `dashboard.kpi()`
đã tồn tại (PRD-001) nhưng **chưa expose** endpoint. CR này bổ sung endpoint, **giữ
nguyên kiến trúc**, **không đổi** 5 endpoint cũ.

## 2. Thay đổi
- Thêm route `GET /dashboard/kpi` trong `apps/crm-core/src/crm/api.py`, gọi
  `dashboard.kpi(conn)` (đã có). Không thêm bảng, không đổi schema.

## 3. Request/Response schema
**Request:** `GET /dashboard/kpi` (không tham số, không body).
**Response 200:**
```json
{
  "total_contacts": 0,
  "total_messages": 0,
  "pipeline_by_stage": { "lead":0,"contacted":0,"qualified":0,"proposal":0,"won":0,"lost":0 },
  "win_rate": 0.0
}
```
| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| total_contacts | int | tổng contact |
| total_messages | int | tổng message |
| pipeline_by_stage | object<int> | đếm theo 6 stage |
| win_rate | float | won / (won+lost), 0.0 nếu chưa có |

## 4. Backward compatibility
- ✅ Chỉ **thêm** route mới; 5 endpoint cũ giữ nguyên hành vi & mã trạng thái.
- ✅ Không đổi DB/model. Không breaking change.
- ✅ Test: 14 test cũ vẫn PASS + 3 test mới (`test_dashboard_endpoint.py`), gồm
  `test_existing_endpoints_still_work`.

## 5. OpenAPI
Cập nhật tại `docs/API/openapi-crm-core.yaml` (thêm path `/dashboard/kpi`).

## 6. Go-live impact
Gỡ gap PRD-003 §11 → WF050 có thể bật node `Read KPI` với `{{$env.CRM_BASE}}/dashboard/kpi`.
