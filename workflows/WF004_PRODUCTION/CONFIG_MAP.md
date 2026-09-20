# WF004 — CONFIG MAP (node `Config`)

> Không phải secret. Điền trong node `Config` (Set) — downstream tham chiếu `$('Config').item.json.<key>`.

| Key | Ý nghĩa | Ví dụ / mặc định | Node dùng |
|---|---|---|---|
| `crm_base` | Base URL CRM nội bộ | `http://crm-core:8080` (đã điền sẵn) | CRM Update, Audit, Metrics |
| `vertex_stt_url` | Endpoint Vertex Speech-to-Text | `https://<region>-aiplatform.googleapis.com/v1/projects/<proj>/locations/<region>/...:recognize` | Vertex STT |
| `vertex_summary_url` | Endpoint Vertex summary/LLM | `https://<region>-aiplatform.googleapis.com/v1/projects/<proj>/locations/<region>/publishers/google/models/<model>:generateContent` | AI Summary |
| `telegram_chat_id` | Chat/Channel id nhận thông báo | `-1001234567890` | Telegram Notify |

- Đổi `crm_base` nếu n8n không cùng network với crm-core (vd `http://<VPS_IP>:8080` nếu đã publish port).
- URL Vertex phụ thuộc region/project/model của Anh — điền đúng của Anh.
