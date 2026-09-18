# Security Hardening — OMI Platform (PRD-005 §9)

## 1. AuthN/AuthZ
- JWT HS256 + refresh (PRD-002); `AUTH_SECRET` mạnh (≥32 bytes) qua env, xoay định kỳ.
- RBAC 4 roles (Admin/Manager/Operator/Viewer); mọi endpoint nhạy cảm qua middleware.
- Mật khẩu: bcrypt (không lưu plaintext).

## 2. Edge (nginx)
- **Rate limit:** 10r/s/IP, burst 20 → 429 (chống brute-force/DoS nhẹ).
- **CORS:** chỉ origin hợp lệ (map `$omi_cors`).
- **CSP:** `default-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`.
- **Headers:** HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy.
- `server_tokens off`; redirect 80→443; TLS1.2/1.3.

## 3. Container
- Base slim, chạy **non-root** (uid 10001/10002).
- Chỉ mount volume cần thiết; data ở `/data` (volume riêng).
- Không bake secret vào image; truyền qua env compose.

## 4. Secrets
- `.env` gitignored; repo chỉ có `.env.example` (không giá trị thật).
- GitHub: repo/Environment secrets cho CI/CD; environment `production` cần approval.

## 5. Dữ liệu
- Backup định kỳ + test restore (DR).
- SQLite file quyền hạn chế; cân nhắc mã hoá volume ở hạ tầng.

## 6. Giám sát bảo mật
- Audit log (PRD-002) cho login/logout/refresh/access_denied.
- Alert khi tỉ lệ 401/403/429 tăng bất thường.

## 7. Checklist nhanh
- [ ] AUTH_SECRET đặt & mạnh
- [ ] HTTPS bắt buộc, HSTS bật
- [ ] Rate limit + CSP + headers hoạt động (kiểm tra bằng curl -I)
- [ ] Không secret trong repo/image
- [ ] Container non-root
- [ ] Backup chạy + restore đã test
