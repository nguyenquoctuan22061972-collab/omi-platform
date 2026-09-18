# Production Checklist — OMI Platform (PRD-005)

## Trước khi go-live
- [ ] `deploy/.env` đặt đầy đủ (OMI_DOMAIN, LETSENCRYPT_EMAIL, **AUTH_SECRET mạnh**)
- [ ] DNS trỏ domain → server; mở port 80/443
- [ ] `apps/dashboard/config.js` đặt `CRM_BASE=/api/crm`
- [ ] SSL cấp thành công (certbot) — HTTPS hoạt động, 80→443 redirect
- [ ] `docker compose ... up -d` — 4 service Up, healthcheck xanh
- [ ] Security headers/CSP/HSTS kiểm tra (`curl -I https://<domain>`)
- [ ] Rate limit hoạt động (spam → 429)
- [ ] CORS chỉ cho origin hợp lệ
- [ ] Container chạy non-root
- [ ] Backup cron cài + chạy thử; **restore đã test**
- [ ] Alerting (healthcheck fail → webhook) hoạt động
- [ ] CI xanh trên `main`; deploy qua workflow `Deploy (manual)` + Environment approval

## Sau go-live
- [ ] Theo dõi logs/executions 24h đầu
- [ ] Xác nhận WF050 KPI (nếu bật automation) đọc `/dashboard/kpi`
- [ ] Lịch DR test hàng quý đã đặt

## Không phá vỡ
- [ ] PRD-001..004 nguyên vẹn (chỉ thêm `deploy/`, `.github/workflows/`, docs)
- [ ] Toàn bộ test-suite PASS trong CI
