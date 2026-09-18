# Contacts Domain (PRD-006 Module A)

Additive dưới `apps/dashboard/contacts/`. Standalone (không sửa PRD-004).

- **contact list** + **search** (tên/phone/email) + **filter** (kênh) + **pagination** (5/trang)
- **contact detail** (click hàng)
- **mock integration layer** (`api.js`, đọc `mock/contacts.json`)

Không đổi API hiện có. Điểm nối `GET /contacts` (list) khi có endpoint tương lai.

## Chạy
`cd apps/dashboard && python3 -m http.server 8000` → `http://localhost:8000/contacts/`
