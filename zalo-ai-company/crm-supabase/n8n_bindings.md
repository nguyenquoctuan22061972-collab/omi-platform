# PR-003 — n8n ↔ Supabase Bindings

CRM chuyển từ SQLite (apps/crm-core) sang Supabase PostgREST. n8n gọi bảng qua REST.

## Credential (n8n) — KHÔNG commit
- `Supabase API` credential: host = `SUPABASE_URL`, service_role key (secret).
- Hoặc HTTP Header Auth: `apikey` + `Authorization: Bearer <service_role>` (đặt trong credential).

## Endpoints (PostgREST)
| Bảng | Endpoint | Dùng ở workflow |
|---|---|---|
| contacts | `{SUPABASE_URL}/rest/v1/contacts` | WF004/WF005 CRM upsert |
| conversations | `{SUPABASE_URL}/rest/v1/conversations` | ghi message |
| pipeline | `{SUPABASE_URL}/rest/v1/pipeline` | cập nhật stage |

## Upsert pattern (n8n httpRequest)
- Header: `Prefer: resolution=merge-duplicates` (upsert theo primary key).
- Method POST tới endpoint bảng; body = row JSON.

## Chuyển WF004/WF005
- Node "CRM Update" đổi Config `crm_base` → không dùng; thay bằng endpoint Supabase + credential.
- Giữ nguyên business logic; chỉ đổi đích ghi (SQLite HTTP → Supabase REST).
