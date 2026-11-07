-- AFFOS 0005 — runtime write access to the operational store, WITHOUT BYPASSRLS. Additive. Idempotent.
-- The durable RevenueStore (PG-backed, when DATABASE_URL is set) writes approvals, idempotency and
-- audit rows as the least-privilege runtime role `affos_service`. It is NOT a member of service_role
-- and has NO BYPASSRLS, so RLS must explicitly permit these specific writes (reads already covered by
-- the authenticated SELECT policies in 0002/0004). Financial tables stay SELECT-only for the runtime.
-- Requires roles.sql (affos_service exists) + 0004 (tables/RLS) applied first.

-- Table-level DML grants (no delete, no truncate, no ddl).
grant select, insert, update on ingestion_approvals   to affos_service;
grant select, insert, update on ingestion_idempotency to affos_service;
grant select, insert         on audit_logs            to affos_service;

-- RLS write policies scoped to the runtime role (no bypass).
drop policy if exists ingestion_approvals_ins_service on ingestion_approvals;
create policy ingestion_approvals_ins_service on ingestion_approvals for insert to affos_service with check (true);
drop policy if exists ingestion_approvals_upd_service on ingestion_approvals;
create policy ingestion_approvals_upd_service on ingestion_approvals for update to affos_service using (true) with check (true);

drop policy if exists ingestion_idempotency_ins_service on ingestion_idempotency;
create policy ingestion_idempotency_ins_service on ingestion_idempotency for insert to affos_service with check (true);
drop policy if exists ingestion_idempotency_upd_service on ingestion_idempotency;
create policy ingestion_idempotency_upd_service on ingestion_idempotency for update to affos_service using (true) with check (true);

drop policy if exists audit_logs_ins_service on audit_logs;
create policy audit_logs_ins_service on audit_logs for insert to affos_service with check (true);
