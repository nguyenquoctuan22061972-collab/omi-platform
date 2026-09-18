# libs/integrations — Adapter Architecture (PRD-006 Module D)

Interface thống nhất cho tích hợp bên thứ ba. **Dry-run**: không gọi API thật;
credential đọc từ env; không hardcode secret.

## Provider
telegram · gmail_smtp · zalo_oa · facebook_messenger · openai · vertex_ai

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

## Go-live
Gắn credential env tương ứng + hiện thực `send()` thật ở phase sau (giữ interface).
Hiện tại luôn dry-run để an toàn.
