# WF004 — CREDENTIAL MAP

> Token/secret **chỉ** nằm trong n8n credential store — KHÔNG commit, KHÔNG dán chat.

| Credential (n8n type) | Nội dung | Gán cho node | Node type |
|---|---|---|---|
| **Google API** (`googleApi`) | Service account (Vertex AI: Speech-to-Text + LLM/summary) | **Vertex STT** | httpRequest (predefinedCredentialType) |
| **Google API** (`googleApi`) | (dùng lại cùng service account) | **AI Summary** | httpRequest (predefinedCredentialType) |
| **Telegram API** (`telegramApi`) | Bot token (BotFather) | **Telegram Notify** | telegram |

Ghi chú:
- CRM Update / Audit / Metrics **không cần credential ngoài** (gọi nội bộ `crm_base`).
- Sau khi gán credential → **enable** node tương ứng.
- Scope Google tối thiểu: Vertex AI (`https://www.googleapis.com/auth/cloud-platform`).
