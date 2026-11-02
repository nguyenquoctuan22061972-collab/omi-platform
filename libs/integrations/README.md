# libs/integrations — Adapter Architecture (PRD-006 Module D)

Interface thống nhất cho tích hợp bên thứ ba. **Dry-run**: không gọi API thật;
credential đọc từ env; không hardcode secret.

## Provider
telegram · gmail_smtp · zalo_oa · facebook_messenger · openai · vertex_ai · gemini

## Interface (`base.Adapter`)
- `name`, `required_env`
- `is_configured()` · `health()` · `send(payload)` → dry-run

## Dùng
```python
from libs.integrations import get_adapter, list_adapters
a = get_adapter("telegram", env=os.environ)
a.health()          # {configured, missing_env, mode:'dry-run'}
a.send({"text": "hi"})   # {status:'dry-run', ...} — KHÔNG gọi API thật
```

## Gemini — kiểm tra thật (opt-in)
`GeminiAdapter.live_check()` gọi API thật chỉ khi được gọi tường minh; `send()` vẫn dry-run.
```bash
GEMINI_MODEL=gemini-2.5-flash python -m libs.integrations.gemini          # models.list, miễn phí
GEMINI_MODEL=gemini-2.5-flash python -m libs.integrations.gemini --probe  # +1 lệnh ≤8 token
```
Khóa đọc từ `GEMINI_API_KEY`, gửi qua header; kết quả phân loại lỗi `auth` / `rate_limit` / `network` / `not_found`.

## Go-live
Gắn credential env tương ứng + hiện thực `send()` thật ở phase sau (giữ interface).
Hiện tại luôn dry-run để an toàn.
