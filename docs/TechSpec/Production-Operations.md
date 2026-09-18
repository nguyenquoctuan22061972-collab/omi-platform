# Tech Spec — Production Operations Layer (PRD-006)

**PRD:** [`../PRD/PRD-006.md`](../PRD/PRD-006.md) · Additive; giữ ADR/naming hiện có.

## 1. Nguyên tắc
- Frontend: vanilla JS (ES modules) nhất quán PRD-004; mỗi domain **standalone**
  (`index.html` riêng) để không sửa `apps/dashboard/src/*` (PRD-004).
- Backend adapter: Python package `libs/integrations/` — interface thống nhất, **dry-run**,
  credential từ env, không network.
- Mock-first: mọi domain đọc mock JSON; integration layer trừu tượng để nối API thật sau.

## 2. Module D — Adapter interface (chuẩn hoá)
```
class Adapter:
    name: str
    required_env: list[str]
    def __init__(env): self.config = {k: env.get(k) for k in required_env}
    def is_configured() -> bool     # đủ env chưa
    def health() -> dict            # {adapter, configured, mode:'dry-run'}
    def send(payload) -> dict       # dry-run: trả {status:'dry-run', ...}; KHÔNG gọi API
```
Provider: telegram, gmail_smtp, zalo_oa, facebook_messenger, openai, vertex_ai.
`registry.get_adapter(name, env)`; `registry.ADAPTERS`.

## 3. Module A/B/C/E — Frontend
| Domain | File chính | Mock |
|---|---|---|
| Contacts | `contacts/contacts.js` (+ api.js) | `contacts/mock/contacts.json` |
| Inbox | `inbox/inbox.js` (+ adapters.js) | `inbox/mock/messages.json` |
| Pipeline | `pipeline/pipeline.js` | `pipeline/mock/deals.json` |
| Operations | `operations/operations.js` | `operations/mock/ops.json` |

- Contacts: search/filter/pagination client-side trên mock; integration layer `getContacts()`
  đọc mock (điểm nối `GET /contacts` sau, không đổi API).
- Inbox: unified list + adapter UI cho 4 kênh (placeholder), chọn kênh → hiển thị nguồn.
- Pipeline: Kanban 6 stage (đồng bộ PRD-001 pipeline), deal detail + activity timeline (mock).
- Operations: thẻ container/workflow/backup/CI/deploy/alert từ `ops.json` (mock).

## 4. Bảo mật
Không secret literal; adapter env-only; validator kiểm tra. Không gọi API thật (dry-run).

## 5. QA / CI
- Validator python cho từng domain (đặt trong `apps/dashboard/tests/` → CI dashboard step tự chạy).
- `libs/integrations/tests/` → thêm CI step riêng.
- Không đổi test cũ → CI giữ xanh.

## 6. Không phá vỡ
Chỉ thêm `libs/`, `apps/dashboard/{contacts,inbox,pipeline,operations}/`, docs mới, test mới,
1 CI step. Không sửa PRD-001..005, router/app.js, capability-map, ADR.
