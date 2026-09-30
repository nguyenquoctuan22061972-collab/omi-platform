# AFFOS Connector · AWIN (PRD-017)

Real affiliate network = AWIN Publisher API. Interface đồng nhất connector layer (reuse, no fork).

## Trạng thái
- **Dry-run:** chạy toàn chuỗi bằng seed (offers + report) → pipeline tính revenue/profit thật.
- **Live:** cần credential → gọi API thật. Chưa bật trong repo (an toàn).

## Credential (env, KHÔNG commit) — PR-005
- `AWIN_API_TOKEN` (OAuth2 bearer token của publisher)
- `AWIN_PUBLISHER_ID`

## Endpoints (không phải secret)
- base `https://api.awin.com`
- transactions: `/publishers/{publisherId}/transactions/?startDate&endDate` (Bearer token)
- aggregated report: `/publishers/{publisherId}/reports/aggregated/publisher`

## Go-live
1. Đặt 2 env ở trên (deploy/.env, gitignored).
2. Bật live path trong `awin_connector.fetch_report()` (parse transactions → {product_id, clicks, conversions}).
3. `pipeline.run(connector=AwinConnector(env))` → REAL offer→click→conversion→commission→revenue→profit.
