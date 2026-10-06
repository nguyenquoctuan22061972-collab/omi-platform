# Impact connector (AFFOS.1)

Isolated provider module for **impact.com**. Additive; does not touch the AWIN connector.

- `impact_connector.py` — seed/DRY-RUN connector (offline catalog, `source=impact_seed`, SEEDED).
- `impact_live.py` — LIVE adapter scaffold: real HTTPS transport (HTTP Basic auth,
  `IMPACT_ACCOUNT_SID:IMPACT_AUTH_TOKEN`), offers (Catalog Items), tracking links, Actions →
  conversion+commission. Production transport never returns seed; failures stay non-real.
- `ImpactAdapter` (in `../adapters.py`) exposes the 8-capability `Connector` interface;
  `get_connector("impact", env, transport)`.

## Economic-truth status (DRY-RUN this sprint)
- Credentials: `IMPACT_ACCOUNT_SID`, `IMPACT_AUTH_TOKEN` (env secrets only — never in Git/logs).
- `impact_production` is **NOT** in `provenance.PRODUCTION_SOURCES` yet, so Impact records are
  **never `is_real()`** — even with a production transport — until the CTO explicitly whitelists it.
- No live Impact API call is wired into any automated path this sprint.

## Impact API (reference)
- Base `https://api.impact.com`, HTTP Basic auth (AccountSID:AuthToken).
- Offers: `/Mediapartners/{sid}/Catalogs/Items` · Links: `/Mediapartners/{sid}/TrackingLinks`
  · Actions (conversions/commissions): `/Mediapartners/{sid}/Actions`.
