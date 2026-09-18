# n8n — Rollback (PRD-007 C)

Khi workflow lỗi sau khi bật. Mục tiêu: dừng thiệt hại, về trạng thái ổn định.

## Quyết định nhanh
```
Workflow lỗi?
├─ Lỗi credential/binding → tắt Active workflow → sửa credential → verify lại
├─ Lỗi node vừa bật → set node về Disabled → workflow chạy phần còn lại an toàn
├─ Lỗi logic import (JSON) → re-import bản Git trước:
│     git checkout <commit_tốt> -- workflows/WFxxx/workflow.json  → Import lại
└─ Không rõ → Deactivate workflow (Active → off) để dừng hẳn, điều tra
```

## Bước an toàn
1. **Deactivate** workflow lỗi (ngừng nhận trigger).
2. Xem n8n Executions để xác định node/lỗi.
3. Áp cách xử lý theo cây trên.
4. **Verify** (`verify.md`) trước khi Active lại.
5. Ghi lại (thời điểm, workflow, nguyên nhân) — postmortem nếu ảnh hưởng khách hàng.

## Nguyên tắc
- Không sửa business logic node để "chữa cháy" — chỉ tắt/bật + credential + re-import bản Git.
- Dữ liệu nằm ở CRM Core; rollback n8n không mất dữ liệu CRM.
