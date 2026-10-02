# AFFOS Ops

Operational preflight for REAL-COMMERCE GATE #1.

## `production_preflight.py`

Reports 8 gates and an overall `ready_for_live_call`. Safe to run in the Builder
(build/test) environment or on the Production VPS (live commerce execution).

- Never prints secrets — credentials report `PRESENT`/`MISSING` only.
- Never makes an authenticated AWIN commerce call. The real call stays the separately
  approved step `connectors/awin/gate1_preflight.live_verify(env, approved=True, transport=ProductionTransport())`,
  to be run **only after** every required gate here is green.

Run:

```bash
cd AFFOS/ops && python3 production_preflight.py           # all gates
cd AFFOS/ops && python3 production_preflight.py --no-tests # skip the test-suite gate
```

Gates: AWIN credentials · AWIN API reachability · Postgres connectivity · Postgres
write · Connector Interface · AWIN adapter · Secret scan · Tests.

The live commerce call is permitted only when `ready_for_live_call` is `True`.
