-- PR-003 CRM Supabase — seed mẫu (KHÔNG phải dữ liệu thật/secret). Idempotent.
insert into contacts (id, name, phone, email, source, tags, created_at) values
  ('c_demo_1','Demo Lead','+84900000001','lead1@demo.local','zalo','vip', now())
  on conflict (id) do nothing;
insert into conversations (id, contact_id, channel, message, timestamp) values
  ('m_demo_1','c_demo_1','zalo','Xin bảng giá', now())
  on conflict (id) do nothing;
insert into pipeline (contact_id, stage) values
  ('c_demo_1','contacted')
  on conflict (contact_id) do update set stage = excluded.stage;
