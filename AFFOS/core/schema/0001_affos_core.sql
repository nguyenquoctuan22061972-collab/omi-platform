-- AFFOS core data model (PRD-017). Postgres. Idempotent. Không secret.
-- id: text pk (gen_random_uuid()::text). money: numeric(18,2). ts: timestamptz default now().

create table if not exists affiliate_networks (
  id text primary key default gen_random_uuid()::text,
  name text not null, type text, status text not null default 'active', created_at timestamptz not null default now()
);
create table if not exists merchants (
  id text primary key default gen_random_uuid()::text,
  network_id text references affiliate_networks(id) on delete set null,
  name text not null, status text not null default 'active', created_at timestamptz not null default now()
);
create table if not exists products (
  id text primary key default gen_random_uuid()::text,
  merchant_id text references merchants(id) on delete cascade,
  sku text, title text not null, price numeric(18,2), currency text not null default 'VND',
  url text, created_at timestamptz not null default now()
);
create table if not exists offers (
  id text primary key default gen_random_uuid()::text,
  product_id text references products(id) on delete cascade,
  merchant_id text references merchants(id) on delete cascade,
  commission_rate numeric(6,4), payout_type text, terms text,
  active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists channels (
  id text primary key default gen_random_uuid()::text,
  platform text not null, handle text, owner text, status text not null default 'active',
  created_at timestamptz not null default now()
);
create table if not exists content (
  id text primary key default gen_random_uuid()::text,
  channel_id text references channels(id) on delete cascade,
  type text, title text, url text, status text not null default 'draft',
  published_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists campaigns (
  id text primary key default gen_random_uuid()::text,
  offer_id text references offers(id) on delete set null,
  channel_id text references channels(id) on delete set null,
  name text not null, status text not null default 'draft',
  budget numeric(18,2), start_at timestamptz, end_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists tracking_links (
  id text primary key default gen_random_uuid()::text,
  campaign_id text references campaigns(id) on delete cascade,
  offer_id text references offers(id) on delete set null,
  slug text unique, target_url text not null, created_at timestamptz not null default now()
);
create table if not exists click_events (
  id text primary key default gen_random_uuid()::text,
  tracking_link_id text references tracking_links(id) on delete cascade,
  ts timestamptz not null default now(), ip_hash text, ua text, referrer text
);
create table if not exists conversion_events (
  id text primary key default gen_random_uuid()::text,
  click_event_id text references click_events(id) on delete set null,
  offer_id text references offers(id) on delete set null,
  order_value numeric(18,2), currency text not null default 'VND',
  status text not null default 'pending', ts timestamptz not null default now()
);
create table if not exists commissions (
  id text primary key default gen_random_uuid()::text,
  conversion_event_id text references conversion_events(id) on delete cascade,
  amount numeric(18,2) not null, currency text not null default 'VND',
  status text not null default 'pending', paid_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists expenses (
  id text primary key default gen_random_uuid()::text,
  campaign_id text references campaigns(id) on delete set null,
  category text, amount numeric(18,2) not null, currency text not null default 'VND',
  ts timestamptz not null default now()
);
create table if not exists revenue (
  id text primary key default gen_random_uuid()::text,
  source text not null, ref_id text, amount numeric(18,2) not null,
  currency text not null default 'VND', ts timestamptz not null default now()
);
create table if not exists customers (
  id text primary key default gen_random_uuid()::text,
  channel_id text references channels(id) on delete set null,
  external_id text, email_hash text, created_at timestamptz not null default now()
);
create table if not exists experiments (
  id text primary key default gen_random_uuid()::text,
  campaign_id text references campaigns(id) on delete cascade,
  hypothesis text, variant text, metric text, status text not null default 'running',
  created_at timestamptz not null default now()
);
create table if not exists opportunities (
  id text primary key default gen_random_uuid()::text,
  product_id text references products(id) on delete set null,
  score numeric(6,4), rationale text, status text not null default 'open',
  created_at timestamptz not null default now()
);
create table if not exists agent_registry (
  id text primary key, department text not null, tier text not null default 'worker',
  capabilities text, created_at timestamptz not null default now()
);
create table if not exists skill_registry (
  id text primary key, name text not null, category text not null,
  handler_ref text, created_at timestamptz not null default now()
);
create table if not exists agent_runs (
  id text primary key default gen_random_uuid()::text,
  agent_id text references agent_registry(id) on delete set null,
  skill_id text references skill_registry(id) on delete set null,
  status text not null default 'started', started_at timestamptz not null default now(),
  finished_at timestamptz, meta jsonb
);
create table if not exists audit_logs (
  id text primary key default gen_random_uuid()::text,
  event text not null, actor text, target text, meta jsonb, ts timestamptz not null default now()
);
create table if not exists system_events (
  id text primary key default gen_random_uuid()::text,
  kind text not null, payload jsonb, ts timestamptz not null default now()
);

-- indexes trên FK nóng
create index if not exists idx_products_merchant on products(merchant_id);
create index if not exists idx_offers_product on offers(product_id);
create index if not exists idx_click_link on click_events(tracking_link_id);
create index if not exists idx_conv_click on conversion_events(click_event_id);
create index if not exists idx_comm_conv on commissions(conversion_event_id);
create index if not exists idx_runs_agent on agent_runs(agent_id);
