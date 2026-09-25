-- PR-003 CRM Supabase — 0002 Row Level Security.
-- service_role (n8n backend) bypass RLS mặc định. authenticated: chỉ đọc.
-- anon: không truy cập. Không chứa secret.

alter table contacts       enable row level security;
alter table conversations  enable row level security;
alter table pipeline       enable row level security;

-- Đọc cho user đã đăng nhập (điều chỉnh theo nhu cầu sau).
drop policy if exists contacts_read_auth on contacts;
create policy contacts_read_auth on contacts
    for select to authenticated using (true);

drop policy if exists conversations_read_auth on conversations;
create policy conversations_read_auth on conversations
    for select to authenticated using (true);

drop policy if exists pipeline_read_auth on pipeline;
create policy pipeline_read_auth on pipeline
    for select to authenticated using (true);

-- Ghi: chỉ service_role (n8n). service_role bỏ qua RLS nên không cần policy insert/update cho nó.
-- anon KHÔNG có policy => bị chặn đọc/ghi.
