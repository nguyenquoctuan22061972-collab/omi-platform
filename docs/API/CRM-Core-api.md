# API Specification — CRM Core (PRD-001 §6)

Base URL: `http://<host>:8080` · Content-Type: `application/json; charset=utf-8`.
Khớp 1-1 với `apps/crm-core/src/crm/api.py`. Đúng 5 endpoint PRD, không thêm.

Auth: **MVP chưa gắn** (điểm cắm RBAC CEO/Sales/CSKH/Admin — Risk §11 "Phân quyền sai").

---

## POST /contacts
Tạo contact; tự **merge** nếu trùng phone/email (§9.2).

Request:
```json
{ "name": "An", "phone": "0900000001", "email": "an@x.com", "source": "facebook_messenger", "tags": ["vip"] }
```
Response `201`:
```json
{ "id": "uuid", "name": "An", "phone": "0900000001", "email": "an@x.com",
  "source": "facebook_messenger", "tags": ["vip"], "created_at": "2026-09-18T..." }
```
> Trùng phone/email → trả contact đã hợp nhất (cùng `id`, cùng `created_at`).

---

## GET /contacts/{id}
Response `200`: object contact · `404`: `{ "error": "not found" }`.

---

## POST /messages
Ghi tin nhắn gắn **đúng** contact (§10). Resolve theo `contact_id`, hoặc `phone`/`email` (tạo/merge nếu chưa có).

Request:
```json
{ "contact_id": "uuid", "channel": "telegram", "message": "Xin chào" }
```
hoặc:
```json
{ "phone": "0900000001", "channel": "zalo_oa", "message": "Giá bao nhiêu?" }
```
Response `201`:
```json
{ "id": "uuid", "contact_id": "uuid", "channel": "telegram", "message": "Xin chào", "timestamp": "..." }
```
Lỗi `400`: thiếu cả `contact_id`/`phone`/`email`.

---

## GET /conversations?contact_id={id}
Timeline hội thoại (sắp theo `timestamp`). Không có `contact_id` → toàn bộ.

Response `200`:
```json
[ { "id": "uuid", "contact_id": "uuid", "channel": "telegram", "message": "Xin chào", "timestamp": "..." } ]
```

---

## POST /pipeline/update
Đặt/đổi stage. Stage ∈ {lead, contacted, qualified, proposal, won, lost}.

Request:
```json
{ "contact_id": "uuid", "stage": "won" }
```
Response `200`: `{ "contact_id": "uuid", "stage": "won" }`
Lỗi `400`: stage không hợp lệ, hoặc contact không tồn tại.

---

## Bảng mã trạng thái
| Tình huống | Mã |
|---|---|
| Tạo contact/message | 201 |
| Đọc / cập nhật pipeline | 200 |
| Input sai (stage/thiếu định danh) | 400 |
| Không tìm thấy contact | 404 |
| Route không tồn tại | 404 |
