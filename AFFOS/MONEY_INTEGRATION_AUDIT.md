# MONEY-01 → MONEY-10 Integration Audit (AFFOS)

Snapshot: branch `main`, audited from commit `c45b629`; integrity fixes applied additively on
top. Principle: **REUSE > ADDITIVE > NO-FORK**. No new orchestrator, no engine fork, no
MONEY-11. No live affiliate call, no VPS change, no secrets.

## Inventory

| Engine | Classification | Reused files | Status / acceptance |
|---|---|---|---|
| MONEY-01 Data Foundation | REUSE+EXTEND | `core/schema/0001..0003.sql`, `data_access.py`, `repository.py`, `provenance.py` | Manifest synced (0003 listed; production-vs-test-adapter note). Canonical status + currency + idempotency covered by tests. |
| MONEY-02 Opportunity Miner | REUSE | `agents/product_scout.py`, `economics.opportunity_score`, `opportunities`, connector offer discovery | Forecast score separate from realized ROI (economics vs attribution). Live market feed still unproven (BLOCKED on creds). |
| MONEY-03 Experiment Engine | REUSE+EXTEND (NEW: `core/experiment.py`) | `experiments`, `opportunities`, `campaigns`, proof scope | Lifecycle state machine DRAFT→NEEDS_APPROVAL→APPROVED→RUNNING→MEASURED→WIN/ITERATE/KILL with audit + idempotency + kill switch; `policy_gate` (budget/loss/currency/approval); `experiment_result()` contract. No orchestrator, no proof/attribution duplication. |
| MONEY-04 AI Affiliate Autopilot | REUSE+EXTEND | `commercial_output.py` (DRY-RUN), adapters, `runtime/server.py`, attribution | Offer discovery (Catalogs→Items), tracking link, Actions ingestion wired; real link/attribution gated. |
| MONEY-05 AI Agent Economy | REUSE; NEW later | `agent_registry`, `skill_registry`, `agent_runs` | No marketplace built before revenue proof (per brief). |
| MONEY-06 Capital Engine | REUSE+EXTEND | `economics.py`, Product Scout cost limits, `ops/production_preflight.py` | Budget/cap/approval extensions are future; no auto-reinvest of unverified profit. |
| MONEY-07 Autonomous CEO Loop | REUSE+EXTEND (CONFLICT if 2nd orchestrator) | runtime/HTTP boundary, n8n | No new orchestrator created. Contract/report only. |
| MONEY-08 Revenue Proof | REUSE+FIX; BLOCKED | `provenance.py`, `proof.py`, AWIN/Impact live adapters, ingest, preflight | Proof is scoped + requires attribution linkage now. Production proof BLOCKED on creds/egress/LIVE DB. |
| MONEY-09 Profit Optimization | REUSE+FIX | `economics.contribution_profit`, attribution EPC/CR, `ai_revenue_ratio` | P0-1..P0-5 fixed (status, refund, zero-revenue, currency, label). Optimize only on reconciled production data. |
| MONEY-10 Scale & Dominance | REUSE; after proof | opportunity scores, experiment outcomes, budget guards | Not enabled; gated on positive reconciled net profit. |

## P0 correctness fixes applied (additive, with regression tests)

| # | Issue | Fix | Test |
|---|---|---|---|
| P0-1 | Status mismatch (`confirmed` vs `APPROVED`) dropped production revenue | `core/money_status.py` canonical sets; attribution matches case-insensitive APPROVED/CONFIRMED | `test_money_integrity.TestStatusCanonical` |
| P0-2 | Refund double-counted | net revenue = Σ confirmed − Σ refund, folded once; refund no longer also a cost | `TestRefundSemantics` |
| P0-3 | Zero revenue flagged healthy | `ai_revenue_ratio` → `status=NO_REVENUE_DATA`, `healthy=False` when revenue ≤ 0 | `TestZeroRevenueHealth` |
| P0-4 | Currency summed blindly | `attribution.totals` groups by currency; multiple → `mixed_currency`, `revenue=None`, `by_currency`; `currency=` filter | `TestCurrencyAggregation` |
| P0-5 | `revenue_label` called LIVE = PRODUCTION_REVENUE | PRODUCTION_REVENUE only for PRODUCTION_VERIFIED; LIVE → UNVERIFIED_REVENUE | `TestRevenueLabel` |
| P0-6 | Proof not experiment-scoped | `real_commerce_proof(repo, campaign_id=...)` scopes via campaign→link→click→conv→comm | `TestProofScopeAndLinkage` |
| P0-7 | Attribution linkage (empty `tracking_link_id`) | proof reports `attribution_linked`; VERIFIED now requires linkage | `TestProofScopeAndLinkage` |
| P0-8 | Manifest/migration doc drift | `schema.manifest.json` lists `0003`; production-vs-test-adapter note added | n/a (doc) |
| — | Idempotency | `repo.insert` upserts by id (SQLite INSERT OR REPLACE / Postgres ON CONFLICT); re-ingest is idempotent | `TestIdempotentIngest` |

## Remaining blockers (not code — external / approval)

- Impact/AWIN credentials, egress, and a LIVE Postgres are required before any real ingestion;
  this session cannot reach the VPS and makes no authenticated call.
- Attribution end-to-end requires the network click reference / sub-ID to populate
  `tracking_link_id` on ingested clicks; until then proof reports attribution as limited.

## Revenue Experiment #001 — status

`BLOCKED` for revenue/profit proof (no verified production transaction). Code path is ready:
single market (US), single network (AWIN first if the account is live, else Impact), single
currency (USD), organic traffic, paid spend 0 until approved. No `seed://` link or expected-
commission estimate is accepted as revenue evidence.
