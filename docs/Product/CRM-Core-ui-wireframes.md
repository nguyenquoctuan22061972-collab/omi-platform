# UI Wireframes — CRM Core (PRD-001 §8)

5 màn hình đúng PRD §8. Wireframe văn bản (low-fi), gắn với API/§dữ liệu tương ứng.
Không thêm màn hình ngoài PRD.

## 1. Dashboard  (Đầu ra §5 "Dashboard KPI")
Nguồn: `GET` KPI (dashboard.kpi).
```
+------------------------------------------------------------+
| OMI CRM   [Dashboard] Contacts Inbox Pipeline              |
+------------------------------------------------------------+
| [ Tổng contacts ]  [ Tổng tin nhắn ]  [ Win rate % ]       |
|      1,240              8,930              27%              |
+------------------------------------------------------------+
| Pipeline theo stage (bar):                                 |
| lead ▓▓▓▓  contacted ▓▓▓  qualified ▓▓  proposal ▓ won ▓ lost ▓ |
+------------------------------------------------------------+
```

## 2. Contact List
Nguồn: danh sách contacts.
```
+------------------------------------------------------------+
| Contacts            [🔍 tìm tên/phone/email]   [+ Contact] |
+------------------------------------------------------------+
| Tên     | Phone      | Kênh(source) | Tags     | Stage     |
|---------|------------|--------------|----------|-----------|
| An      | 0900000001 | facebook     | vip      | qualified |
| Bình    | 0900000002 | zalo_oa      | pricing  | lead      |
+------------------------------------------------------------+
| (click hàng → Contact Detail)                              |
```

## 3. Conversation Inbox
Nguồn: `GET /conversations` (+ filter contact).
```
+---------------------+--------------------------------------+
| Hội thoại           |  An — 0900000001   [telegram]        |
|---------------------|--------------------------------------|
| ● An     telegram   |  10:01  An: Xin chào                 |
|   Bình   zalo_oa    |  10:02  Sales: Chào anh...           |
|   ...               |  [ nhập tin nhắn ......... ] [Gửi]   |
+---------------------+--------------------------------------+
```

## 4. Pipeline Kanban
Nguồn: pipeline stage (POST /pipeline/update khi kéo-thả).
```
+--------+-----------+-----------+----------+-------+-------+
| lead   | contacted | qualified | proposal | won   | lost  |
|--------|-----------|-----------|----------|-------|-------|
| [Bình] | [Chi]     | [An]      | [Dũng]   |[Em]   |[Phúc] |
| [....] |           |           |          |       |       |
+--------+-----------+-----------+----------+-------+-------+
| (kéo thẻ giữa cột → gọi POST /pipeline/update)            |
```

## 5. Contact Detail
Nguồn: `GET /contacts/{id}` + `GET /conversations?contact_id=`.
```
+------------------------------------------------------------+
| ← An            phone 0900000001   email an@x.com          |
| source: facebook_messenger   tags: [vip][pricing]         |
| stage: [ qualified ▼ ]  (đổi → POST /pipeline/update)      |
+------------------------------------------------------------+
| Timeline hội thoại:                                        |
|  10:01 telegram  An: Xin chào                              |
|  10:02 telegram  Sales: ...                                |
+------------------------------------------------------------+
```

## Ghi chú
- Wireframe chỉ mô tả bố cục & luồng dữ liệu; **chưa gồm code frontend** (ngoài
  phạm vi PRD-001, cần PRD/TechSpec UI riêng nếu triển khai app web).
- Mọi hành động đọc/ghi ánh xạ tới 5 endpoint trong `../API/CRM-Core-api.md`.
