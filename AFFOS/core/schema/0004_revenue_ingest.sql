-- AFFOS Revenue Ingestion durable persistence (S5A). Postgres. Idempotent. No secret.
-- Additive: new tables + indexes only; does not alter existing financial tables' data.
-- Applied on the VPS under a SEPARATE approval (not by this PR). RLS mirrors 0002_rls.sql:
-- service_role writes (bypass); authenticated reads; anon blocked.

-- ---- Approvals: scoped, time-windowed, expiring, auditable ----
create table if not exists ingestion_approvals (
  id            text primary key default gen_random_uuid()::text,
  provider      text not null,
  environment   text not null,
  window_start  timestamptz not null,
  window_end    timestamptz not null,
  expires_at    timestamptz not null,
  status        text not null default 'active',          -- active | revoked | expired
  granted_by    text,
  granted_at    timestamptz not null default now(),
  revoked_by    text,
  revoked_at    timestamptz,
  constraint ingestion_approvals_window_ck check (window_end >= window_start)
);
create index if not exists ix_appr_lookup on ingestion_approvals(provider, environment, status);

-- ---- Request-level idempotency: PK gives atomic single-writer under concurrency ----
create table if not exists ingestion_idempotency (
  idem_key    text primary key,
  body_hash   text not null,
  response    jsonb,
  created_at  timestamptz not null default now()
);
-- Retention (run as a scheduled job under ops approval; NOT scheduled by this PR):
--   delete from ingestion_idempotency where created_at < now() - interval '30 days';
--   update ingestion_approvals set status='expired' where status='active' and expires_at <= now();

-- ---- Row-level dedupe (defense-in-depth): one provider action id -> one financial row ----
create unique index if not exists ux_commissions_src       on commissions(source, source_record_id);
create unique index if not exists ux_conversion_events_src on conversion_events(source, source_record_id);
create unique index if not exists ux_click_events_src      on click_events(source, source_record_id);

-- ---- RLS (same posture as 0002) ----
alter table ingestion_approvals   enable row level security;
drop policy if exists ingestion_approvals_read_auth on ingestion_approvals;
create policy ingestion_approvals_read_auth on ingestion_approvals for select to authenticated using (true);
alter table ingestion_idempotency enable row level security;
drop policy if exists ingestion_idempotency_read_auth on ingestion_idempotency;
create policy ingestion_idempotency_read_auth on ingestion_idempotency for select to authenticated using (true);
