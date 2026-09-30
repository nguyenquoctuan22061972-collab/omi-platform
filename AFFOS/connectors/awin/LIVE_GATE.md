# AWIN LIVE GATE (PRD-017 / CTO review)

REAL COMMERCE PROOF chỉ = VERIFIED khi TOÀN BỘ chuỗi dưới đây độc lập xác minh từ production Awin.
Đến khi đó: **REAL COMMERCE PROOF: NOT YET VERIFIED**. Seeded/dry-run KHÔNG BAO GIỜ gọi là REAL.

## Điều kiện LIVE (mỗi mục phải verified)
1. [ ] Awin production credential (`AWIN_API_TOKEN`)
2. [ ] Awin publisher ID (`AWIN_PUBLISHER_ID`)
3. [ ] Production Postgres/Supabase (`DATABASE_URL`/`SUPABASE_DB_URL`) qua PostgresRepository
4. [ ] Real offer/program retrieval (Awin programmes joined)
5. [ ] Real affiliate/deep-link generation (Awin click ref)
6. [ ] Real tracking (AFFOS_TRACKED_CLICK hoặc NETWORK_REPORTED_CLICK)
7. [ ] Real transaction ingestion (Awin /transactions → AWIN_PRODUCTION_CONVERSION)
8. [ ] Real commission (từ Awin transaction, data_state=PRODUCTION_VERIFIED, is_verified)
9. [ ] Real revenue (PRODUCTION_REVENUE)
10. [ ] Real contribution profit (từ #9 − chi phí thật)

## Tiêu chí chấp nhận (CTO): economic truth over test success
- `proof.real_commerce_proof(repo)` == "VERIFIED" (mọi conversion+commission là is_real).
- LIVE adapter = PostgresRepository (SQLite bị cấm cho LIVE).
- KHÔNG mở rộng 800-agent workforce và KHÔNG thêm affiliate network khác cho tới khi Awin proof VERIFIED.
