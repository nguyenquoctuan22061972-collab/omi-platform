# AI Playbook — OMI Platform (PRD-009 H)

Hướng dẫn dùng AI trong content-factory. Additive; không đổi tài liệu cũ.

## Kiến trúc AI
- **Prompt Registry** (`libs/prompts`) — prompt version hoá theo 8 loại.
- **AI Router** (`libs/ai_router`) — chọn provider (OpenAI/Vertex/Claude/Gemini) + fallback/retry/timeout.
- **Job Queue** (`apps/content-factory/queue`) — priority/retry/dead-letter.
- **Content Pipeline** (`apps/content-factory/pipeline`) — Topic→…→Publish (state machine).
- **Publish Connectors** (`libs/publish`) — YouTube/TikTok/Facebook/Telegram (dry-run).

## Quy tắc
- Không hardcode key; provider bật theo env.
- Mặc định dry-run tới khi có credential.
- Prompt thay đổi → tăng version (không sửa version cũ).

## Luồng chuẩn
Topic → (Router chọn provider) render prompt (Registry) → Script/Thumbnail/Video →
QA → Publish (connector dry-run). Điều phối qua Job Queue; giám sát qua Autopilot.
