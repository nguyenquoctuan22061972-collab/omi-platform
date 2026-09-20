# WF004 — ROLLBACK

Không xoá file. Rollback = tắt hoạt động, không ảnh hưởng WF001/002/050.

## Mức 1 — Deactivate (nhanh nhất)
1. n8n → WF004 → gạt **Active → off**. Webhook production ngừng nhận.

## Mức 2 — Disable node lỗi
- Nếu 1 node ngoài (Vertex/Telegram) lỗi: gạt node đó về **disabled** (vẫn giữ dây), workflow vẫn chạy các node còn lại.

## Mức 3 — Khôi phục bản import sạch
1. Xoá workflow lỗi trong n8n.
2. Import lại `workflows/WF004.n8n.json` (commit hiện tại) → về trạng thái gốc: 3 node disabled, chưa activate.

## Kiểm tra sau rollback
- WF001/WF002/WF050 vẫn Active bình thường.
- Không còn execution lỗi mới trong Executions log.
