# Tech Spec — CRM-Core: CRM Core

**Tên Module:** CRM Core

**PRD tham chiếu:** [`../PRD/PRD-001.md`](../PRD/PRD-001.md)

## Kiến trúc tổng quan
Dịch vụ CRM Core viết bằng **Python 3.11 stdlib** (không phụ thuộc mạng để chạy
QA offline): `http.server` cho REST API, `sqlite3` cho lưu trữ, `unittest` cho QA.
Kiến trúc phân lớp: **API → Service (module) → DB**. Bám đúng phạm vi PRD-001,
không thêm chức năng ngoài PRD.

```
Channels (FB/Zalo/Telegram/Email/Form/Webhook)
      │  (normalize)
      ▼
  ingestion ──► contacts (merge) ──► tagging (AI stub)
      │                                   │
      ▼                                   ▼
  conversations ───────────────► pipeline ───► dashboard (KPI)
                          (SQLite storage)
```

## Thành phần & trách nhiệm (map 1-1 với module code)
| Module | File | Trách nhiệm | API PRD |
|---|---|---|---|
| db | `src/crm/db.py` | Kết nối SQLite, tạo schema, truy vấn | — |
| models | `src/crm/models.py` | Kiểu dữ liệu Contact/Conversation | — |
| contacts | `src/crm/contacts.py` | Tạo/đọc contact + **merge theo phone/email** | POST /contacts, GET /contacts/{id} |
| conversations | `src/crm/conversations.py` | Ghi message gắn đúng contact, đọc timeline | POST /messages, GET /conversations |
| pipeline | `src/crm/pipeline.py` | Cập nhật giai đoạn pipeline hợp lệ | POST /pipeline/update |
| tagging | `src/crm/tagging.py` | Auto-tag (rule-based stub cho "AI gắn tag") | — |
| dashboard | `src/crm/dashboard.py` | Tổng hợp KPI realtime | — (Đầu ra: Dashboard KPI) |
| ingestion | `src/crm/ingestion.py` | Chuẩn hoá payload 6 kênh → contact+message | Đầu vào PRD §4 |
| api | `src/crm/api.py` | Router HTTP nối các module | Tất cả endpoint §6 |

## Mô hình dữ liệu (bám PRD §7)
- **contacts**(id PK, name, phone, email, source, tags, created_at)
- **conversations**(id PK, contact_id FK, channel, message, timestamp)
- **pipeline**(contact_id PK/FK, stage) — stage ∈ {lead, contacted, qualified, proposal, won, lost}

## Hợp đồng API (bám PRD §6)
| Method | Path | Body/Params | Response |
|---|---|---|---|
| POST | `/contacts` | {name, phone, email, source} | 201 {contact} (đã merge nếu trùng) |
| GET | `/contacts/{id}` | — | 200 {contact} / 404 |
| POST | `/messages` | {contact_id?, phone?, email?, channel, message} | 201 {conversation} |
| GET | `/conversations` | ?contact_id= | 200 [conversations] |
| POST | `/pipeline/update` | {contact_id, stage} | 200 {contact_id, stage} / 400 stage sai |

## Quy tắc nghiệp vụ (bám PRD §9)
1. **Merge:** contact mới trùng `phone` **hoặc** `email` (không rỗng) với contact có sẵn → cập nhật vào contact cũ, không tạo bản ghi mới (giảm rủi ro R "Trùng dữ liệu").
2. **Tin nhắn đúng contact:** `/messages` resolve contact theo `contact_id`, nếu không có thì theo phone/email (tạo/merge qua ingestion).
3. **AI gắn tag:** `tagging` gán tag theo từ khoá/kênh (stub xác định để test được; điểm cắm cho AI thật sau).
4. **Pipeline hợp lệ:** chỉ nhận 6 stage PRD; stage lạ → 400.
5. **KPI realtime:** dashboard đọc trực tiếp DB tại thời điểm gọi (không cache) → phản ánh tức thời.

## Phụ thuộc
Chỉ Python stdlib: `sqlite3`, `http.server`, `json`, `uuid`, `datetime`, `unittest`.

## Bảo mật & phân quyền
- MVP: chưa gắn auth (ghi rõ trong Risk PRD "Phân quyền sai"). Điểm cắm middleware
  role (CEO/Sales/CSKH/Admin) để mở rộng.
- Không commit secret; input được tham số hoá SQL (chống injection).

## Chiến lược kiểm thử (map PRD §10)
| Test Case PRD | File test |
|---|---|
| Trùng số điện thoại phải merge | `tests/test_contacts_merge.py` |
| Tin nhắn đúng contact | `tests/test_conversations.py` |
| Pipeline cập nhật | `tests/test_pipeline.py` |
| KPI thay đổi theo thời gian thực | `tests/test_dashboard_kpi.py` |

## Kế hoạch triển khai
`python3 apps/crm-core/run.py` chạy server dev cổng 8080. Container hoá & CI để giai
đoạn Deployment sau (ngoài phạm vi PRD-001).

## Rủi ro kỹ thuật (bám PRD §11)
- Trùng dữ liệu → merge rule + unique index mềm theo phone/email.
- Giới hạn API → chưa có rate-limit ở MVP (ghi nhận, làm ở Deployment).
- Mất webhook → ingestion idempotent theo (channel + external ref) là hướng mở rộng.
- Phân quyền sai → điểm cắm RBAC nêu trên.
