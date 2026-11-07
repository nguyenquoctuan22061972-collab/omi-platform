-- AFFOS staging DB bootstrap roles — Option A (dedicated, production-independent Postgres).
-- Run ONCE by a superuser on the STAGING database, BEFORE migrations 0001–0004.
-- Secret-free + idempotent: role LOGIN passwords are set OUT OF BAND (see bottom), never in this file.
-- Rationale: 0002_rls.sql / 0004_revenue_ingest.sql target Supabase role names (authenticated,
-- service_role) and assume service_role bypasses RLS. On a vanilla Postgres these roles do not exist,
-- so the policies fail unless created here. n8n is granted NOTHING (it only calls the API with a JWT).

-- 1) Supabase-compatible roles required by 0002/0004.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon')          then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role')  then create role service_role nologin bypassrls; end if;
end $$;

-- 2) Migration owner — owns the schema, runs 0001–0004 (DDL). NOT used at runtime.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'affos_owner') then create role affos_owner login; end if;
end $$;

-- 3) Runtime application role — least-privilege, DML only, NO DDL. Bypasses RLS for the (future)
--    financial write path, matching the service_role posture; constrained by the GRANTs below.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'affos_service') then create role affos_service login bypassrls; end if;
end $$;
grant authenticated to affos_service;   -- read side (RLS SELECT policies apply)
grant service_role  to affos_service;   -- write side (RLS-bypass posture)

-- 4) Schema usage.
grant usage on schema public to affos_service, authenticated;

-- 5) Owner's FUTURE objects (created during migration) auto-grant least-privilege reads to the runtime.
alter default privileges for role affos_owner in schema public grant select on tables to authenticated, affos_service;

-- 6) Defensive read grant on any already-existing tables (idempotent).
grant select on all tables in schema public to affos_service;

-- ---------------------------------------------------------------------------------------------------
-- POST-MIGRATION, TARGETED WRITE GRANTS (run AFTER 0001–0004, ONLY when the PG write path is wired;
-- today the runtime only reads PG for report/reconcile, so these stay commented for least-privilege):
--   grant insert, update on
--     click_events, conversion_events, commissions, revenue,
--     ingestion_approvals, ingestion_idempotency, audit_logs
--   to affos_service;   -- NO delete, NO truncate, NO ddl
--
-- SET LOGIN PASSWORDS OUT OF BAND (never commit values); e.g. from the secret store:
--   psql "$SUPERUSER_URL" -v owner_pw="$AFFOS_PG_OWNER_PASSWORD"   -c "alter role affos_owner   password :'owner_pw';"
--   psql "$SUPERUSER_URL" -v svc_pw="$AFFOS_PG_PASSWORD"          -c "alter role affos_service password :'svc_pw';"
-- ---------------------------------------------------------------------------------------------------
