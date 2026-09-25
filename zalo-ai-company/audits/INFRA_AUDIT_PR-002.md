# PR-002 — Engineering Infra Audit (2026-09-25)

Nguyên tắc: chỉ audit, KHÔNG sửa. Cột "Nguồn" = verified-from-session hay cần-VPS.

| # | Hạng mục | Kết quả (từ session) | Nguồn |
|---|---|---|---|
| 1 | n8n URL `https://ycdtuo.ezn8n.com` | Không nối được — **403 CONNECT** tại egress proxy | ✅ verified (session) |
| 5 | Webhook HTTPS `/webhook/wf004-call-intelligence` | Cùng 403 — chưa xác minh được từ đây | ✅ verified (session) |
| 6 | Nguyên nhân 403 egress | **Network policy của environment** chặn host ngoài allowlist (`selective:false`; allowlist chỉ gồm Anthropic API + registry gói). Gateway trả 403 cho CONNECT tới `ycdtuo.ezn8n.com:443`. KHÔNG phải lỗi n8n/nginx/SSL. | ✅ verified (proxy status) |
| 2 | VPS (Ubuntu 24.04) | Không có shell trong session → **không audit live được** | ⛔ cần VPS |
| 3 | Docker/Compose + container (n8n, postgres, crm-core...) | Không audit live được từ session | ⛔ cần VPS |
| 4 | Nginx (host `nginx/1.24.0 Ubuntu`) + route `/api/*` | Không audit live được từ session | ⛔ cần VPS |

## Lệnh audit read-only để chạy TRÊN VPS (không sửa gì)
```bash
# 2. VPS
uname -a; uptime; df -h /; free -m
# 3. Docker
docker version --format '{{.Server.Version}}'; docker compose version
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker network ls; docker inspect -f '{{json .NetworkSettings.Networks}}' n8n
# 4. Nginx
nginx -v; nginx -t
ss -tlnp | grep -E ':80|:443|:5678|:8080'
# 5. Webhook HTTPS (từ VPS)
curl -I https://ycdtuo.ezn8n.com
curl -sS -o /dev/null -w '%{http_code}\n' https://ycdtuo.ezn8n.com/webhook/wf004-call-intelligence
```

## Kết luận
403 egress = **chính sách mạng của environment**, sửa ở phía cấu hình environment (không phải code, không phải VPS).
Phần VPS/Docker/Nginx cần một trong hai kênh ở PR-002B để audit/tự động hoá.
