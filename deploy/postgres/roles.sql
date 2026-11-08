-- AFFOS staging DB bootstrap roles — Option A (dedicated, production-independent Postgres).
-- Run ONCE by a superuser on the STAGING database, BEFORE migrations 0001–0004 (+ 0005).
-- Secret-free + idempotent: role LOGIN passwords are set OUT OF BAND (see bottom), never in this file.
--
-- Least-privilege (CTO quality gate):
--   * affos_owner  — owns the schema; runs migrations (DDL). NOT used at runtime.
--   * affos_service — runtime role. NO BYPASSRLS, NOT a member of service_role, NO DDL.
--     Reads via RLS SELECT policies (member of `authenticated`); writes ONLY the operational store
--     tables, granted explicitly by migration 0005 (ingestion_approvals/idempotency, audit_logs).
-- n8n is granted NOTHING (it only calls the API with a JWT).

-- 1) Supabase-compatible GROUP roles required by 0002/0004 policy targets (vanilla Postgres).
--    service_role keeps BYPASSRLS for the (future, deferred) financial write path, but NO runtime
--    role is a member of it.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon')          then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role')  then create role service_role nologin bypassrls; end if;
end $$;

-- 2) Migration owner — owns the schema, runs migrations (DDL). NOT used at runtime.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'affos_owner') then create role affos_owner login; end if;
end $$;

-- 3) Runtime application role — least-privilege, DML only, NO DDL, NO BYPASSRLS, NOT in service_role.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'affos_service') then create role affos_service login; end if;
end $$;
grant authenticated to affos_service;   -- read side ONLY (RLS SELECT policies apply)
-- (intentionally NO `grant service_role to affos_service` and NO bypassrls — writes are scoped by 0005)

-- 4) Schema usage. Owner may CREATE (migrations); runtime/authenticated/anon may NOT (no DDL).
grant usage  on schema public to affos_service, authenticated;
grant create on schema public to affos_owner;
revoke create on schema public from affos_service, authenticated, anon, public;

-- 5) Owner's FUTURE objects (created during migration) auto-grant least-privilege reads to the runtime.
alter default privileges for role affos_owner in schema public grant select on tables to authenticated, affos_service;

-- 6) Defensive read grant on any already-existing tables (idempotent).
grant select on all tables in schema public to affos_service;

-- Write grants + RLS write policies for the operational store tables are in migration
-- 0005_ingest_store_policies.sql (run after 0004). No bypass; writes limited to those tables.
-- ---------------------------------------------------------------------------------------------------
-- SET LOGIN PASSWORDS OUT OF BAND (never commit values); e.g. from the secret store:
--   psql "$SUPERUSER_URL" -v owner_pw="$AFFOS_PG_OWNER_PASSWORD"   -c "alter role affos_owner   password :'owner_pw';"
--   psql "$SUPERUSER_URL" -v svc_pw="$AFFOS_PG_SERVICE_PASSWORD"   -c "alter role affos_service password :'svc_pw';"
-- ---------------------------------------------------------------------------------------------------
