-- Orchestrator job_results — persistent command-path result store (Postgres/LIVE parity).
-- Additive; independent of AFFOS core 21-table schema. Run ONLY on a test/staging DB,
-- never on Production without CTO sign-off and a verified DATABASE_URL (PR-003).
-- ResultStore (orchestrator/runtime/result_store.py) also auto-creates this table via
-- CREATE TABLE IF NOT EXISTS, so this file is the explicit migration record.

CREATE TABLE IF NOT EXISTS job_results (
    correlation_id TEXT PRIMARY KEY,
    task_id        TEXT,
    command        TEXT,
    target         TEXT,
    status         TEXT,              -- QUEUED | RUNNING | SUCCEEDED | FAILED | BLOCKED
    result_json    TEXT,
    error          TEXT,              -- scrubbed of secrets before write
    worker         TEXT,
    capability     TEXT,
    created_at     TEXT,
    updated_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_job_results_task ON job_results (task_id);
CREATE INDEX IF NOT EXISTS idx_job_results_status ON job_results (status);
