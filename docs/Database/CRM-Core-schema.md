# Database Schema — CRM Core (PRD-001 §7)

Khớp 1-1 với `apps/crm-core/src/crm/db.py`. Không thêm bảng/cột ngoài PRD.

## ERD (text)
```
contacts 1 ────< conversations
   │  (contact_id)
   └──1 pipeline (contact_id)
```

## DDL (SQLite)
```sql
CREATE TABLE contacts (
    id          TEXT PRIMARY KEY,   -- uuid4
    name        TEXT,
    phone       TEXT,               -- khoá merge (§9.2)
    email       TEXT,               -- khoá merge (§9.2)
    source      TEXT,               -- kênh nguồn (§4)
    tags        TEXT DEFAULT '',    -- CSV, hợp nhất khi merge
    created_at  TEXT NOT NULL       -- ISO-8601 UTC
);

CREATE TABLE conversations (
    id          TEXT PRIMARY KEY,   -- uuid4
    contact_id  TEXT NOT NULL REFERENCES contacts(id),
    channel     TEXT NOT NULL,      -- §4
    message     TEXT NOT NULL,
    timestamp   TEXT NOT NULL       -- ISO-8601 UTC
);

CREATE TABLE pipeline (
    contact_id  TEXT PRIMARY KEY REFERENCES contacts(id),
    stage       TEXT NOT NULL       -- ∈ {lead,contacted,qualified,proposal,won,lost}
);
```

## Bảng & cột (PRD §7)
### contacts
| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | TEXT PK | uuid4 |
| name | TEXT | |
| phone | TEXT | khoá merge |
| email | TEXT | khoá merge |
| source | TEXT | 1 trong 6 kênh §4 |
| tags | TEXT | CSV; merge không trùng |
| created_at | TEXT | ISO-8601 UTC |

### conversations
| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | TEXT PK | uuid4 |
| contact_id | TEXT FK→contacts.id | bắt buộc |
| channel | TEXT | §4 |
| message | TEXT | |
| timestamp | TEXT | ISO-8601 UTC |

### pipeline
| Cột | Kiểu | Ghi chú |
|---|---|---|
| contact_id | TEXT PK/FK→contacts.id | 1 stage / contact |
| stage | TEXT | 6 giá trị hợp lệ; stage lạ bị từ chối |

## Ràng buộc & quy tắc
- `PRAGMA foreign_keys = ON`.
- **Merge (§9.2):** insert contact trùng `phone` **HOẶC** `email` (khác rỗng) → cập nhật bản ghi cũ, không tạo mới → chống rủi ro "Trùng dữ liệu" (§11).
- `pipeline.stage` giới hạn ở tầng ứng dụng (`models.PIPELINE_STAGES`).

## Migration
MVP tạo schema idempotent qua `db.init_db()`. Migration có phiên bản → giai đoạn Deployment (ngoài phạm vi PRD-001).
