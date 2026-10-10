# Revenue Experiment #001 — Plan (NOT revenue evidence)

This is a **plan**, not proof. Status today: **BLOCKED** (external readiness missing). No live
call, no paid spend, no public publish was performed to write this.

## Fixed parameters
- **Market:** US
- **Network:** AWIN if the account/program is live and verified; otherwise evaluate Impact.
  Do not run both in parallel.
- **Currency:** USD (single — no USD/VND mixing; `attribution.totals(currency="USD")`).
- **Traffic:** organic from content only. **paid_spend = 0** until CEO approves a specific cap.

## To define before launch (recorded in the experiment policy)
- One valid offer/program + demand evidence (source, timestamp).
- One landing/content asset; one real tracking link; one campaign/experiment ID.
- Tracking reference / sub-ID so ingested clicks carry `tracking_link_id` (required for
  end-to-end attribution — without it, proof stays attribution-limited).
- Measurement window, `max_budget`, `max_loss`, success criteria, kill rule — all set in the
  `experiment.Experiment` policy and enforced by `policy_gate` before RUNNING.

## Lifecycle (enforced by core/experiment.py)
`DRAFT → NEEDS_APPROVAL → APPROVED (ceo_approved) → RUNNING (policy_gate OK) → MEASURED →
WIN | ITERATE | KILL`. Kill switch available from any active state.

## Revenue recognition rules (enforced by code)
- Only `APPROVED`/`CONFIRMED` commissions count as revenue; `PENDING`/`DECLINED`/`CANCELLED`
  never do; `REFUNDED`/`REVERSED` subtract once (net = gross − refunds).
- `revenue_proven` requires: verified production transaction (`is_real`) + attribution
  linkage + proof scoped to this campaign. Seed/`seed://`/expected-commission never qualify.

## Readiness gaps (why BLOCKED) — none are code
| Requirement | Status |
|---|---|
| Real network credentials (AWIN or Impact) on the runtime | MISSING |
| Outbound egress to the network API from the runtime | MISSING (Builder proxy blocks it) |
| LIVE Postgres (`affos`) + `DATABASE_URL` on the runtime | MISSING from this session |
| Tracking reference / sub-ID wired into ingested clicks | NOT YET (attribution limited) |

## Exit criteria to move past BLOCKED
Provision the above on the VPS → `ops/production_preflight.py` (and `--impact`) all PASS →
gated ingestion with a real transaction → `experiment_result()` returns
`revenue_proven=True` with `evidence_class=PRODUCTION_VERIFIED`. Only then report
`REVENUE PROVEN` / `PROFIT PROVEN`.
