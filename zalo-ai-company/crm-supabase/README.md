# CRM on Supabase (PR-003)

Migrate schema CRM (contacts/conversations/pipeline) từ SQLite → Supabase, giữ parity 1:1.

## Nội dung
- `migrations/0001_init.sql` — schema (mirror SQLite) + FK + index.
- `migrations/0002_rls.sql` — bật RLS + policy (authenticated đọc; service_role ghi).
- `seed/seed.sql` — dữ liệu mẫu (không secret).
- `src/migrate_planner.py` — planner dry-run: đọc SQLite hiện tại → kế hoạch nạp Supabase.
- `n8n_bindings.md` — endpoint PostgREST + credential.

## Áp dụng (cần PR-003 secret)
1. Tạo Supabase project → lấy `SUPABASE_URL` + `service_role key` (đặt trong `deploy/.env` / credential n8n; KHÔNG commit).
2. Chạy `migrations/0001_init.sql` rồi `0002_rls.sql` (Supabase SQL editor hoặc CLI).
3. (tuỳ chọn) `seed/seed.sql`.
4. Dùng `migrate_planner.plan(<sqlite_path>)` để lấy hàng cũ → đẩy qua PostgREST.
5. Trỏ n8n CRM node sang endpoint Supabase (n8n_bindings.md).
