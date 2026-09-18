# Automation Roadmap — OMI Platform (PRD-009 H)

Lộ trình đạt 90–99% tự động (chỉ chờ credential/runtime).

## Hiện trạng (đã build, additive)
- CRM Core + Auth/RBAC + Dashboard + Automation n8n (skeleton) + Deployment + Ops layer.
- AI Factory: Job Queue · Prompt Registry · AI Router · Content Pipeline · Publish (dry-run).
- CEO Autopilot: dashboard tổng hợp (integration layer).

## Mức tự động
| Giai đoạn | Tự động | Chờ |
|---|---|---|
| Code/skeleton | ~99% | — (đã xong) |
| Runtime dry-run | ~90% | service chạy (VPS) |
| Production thật | mục tiêu 99% | **credential** (AI provider, kênh publish, n8n) |

## Bước bật production (không đổi code)
1. Gắn env credential (AI: OPENAI/VERTEX/ANTHROPIC/GEMINI; Publish: YouTube/TikTok/FB/Telegram).
2. `*_ENABLED=true` cho adapter/provider cần dùng.
3. Bật node n8n disabled (`deploy/n8n/enable-production.md`).
4. Hiện thực `send()/publish()/route()` thật (giữ interface) — thay dry-run.
5. `deploy/go-live.sh <tag>` + `scripts/production-ready.sh`.

## Nguyên tắc
Mọi thành phần additive, interface ổn định → bật production = cấu hình, không viết lại.
