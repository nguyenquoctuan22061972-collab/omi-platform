# WF004 — PRODUCTION VERIFICATION (5 phút)

Baseline: 9 node · 8 connection (đã khớp UI). Tick lần lượt; mỗi mục có PASS + fix 1 bước.

## 1. Google credential bind (~60s)
- Mở **Vertex STT** → Credential Type = **Google API**, chọn credential đã tạo. Lặp cho **AI Summary**.
- **PASS:** cả 2 node hết cảnh báo credential, không viền đỏ.
- **Đỏ →** node: Vertex STT/AI Summary · nguyên nhân: credential trống/sai type · **fix:** chọn lại credential Google API ở ô "Credential Type".

## 2. Telegram credential bind (~30s)
- Mở **Telegram Notify** → credential **Telegram API** (bot token).
- **PASS:** node hết cảnh báo.
- **Đỏ →** node: Telegram Notify · nguyên nhân: chưa gán bot token · **fix:** chọn credential Telegram API.

## 3. Config values (~60s)
- Mở **Config**: `crm_base=http://crm-core:8080`, `vertex_stt_url`, `vertex_summary_url`, `telegram_chat_id` đều có giá trị (không rỗng).
- **PASS:** 4 field có giá trị; URL httpRequest hết đỏ (đã lấy từ `$('Config')`).
- **Đỏ →** node: Vertex/CRM · nguyên nhân: field Config rỗng · **fix:** điền đúng field còn trống trong node Config.

## 4. Publish / Activate (~30s)
- Save → gạt **Active = ON**.
- **PASS:** toggle xanh; có Production URL `/webhook/wf004-call-intelligence`.
- **Đỏ →** không activate được · nguyên nhân: còn node đỏ ở B1–B3 · **fix:** xử lý node đỏ trước rồi Activate.

## 5. POST production webhook (~90s)
- Gửi payload #1 (POSTMAN/HOPPSCOTCH hoặc curl) tới `/webhook/wf004-call-intelligence`.
- **PASS:** HTTP 200; Executions log 1 run xanh tới **Metrics**; CRM có conversation (channel=call); Telegram nhận summary.
- **Đỏ theo node:**
  - **CRM Update/Audit/Metrics** đỏ → nguyên nhân: n8n không tới được `crm-core:8080` · fix: đặt `crm_base` = URL n8n gọi được (cùng docker network, hoặc `http://<VPS_IP>:8080` nếu đã publish port).
  - **Vertex STT/AI Summary** đỏ → nguyên nhân: URL/endpoint hoặc scope Google sai · fix: sửa `vertex_*_url` trong Config cho đúng region/project/model.
  - **Telegram Notify** đỏ → nguyên nhân: chat_id sai hoặc bot chưa vào kênh · fix: sửa `telegram_chat_id` / add bot vào kênh.

## 6. Go / No-Go
- **GO** khi: B1–B4 PASS **và** B5 execution xanh tới Metrics.
- **NO-GO** khi: bất kỳ node đỏ ở B5 → Deactivate (ROLLBACK.md mức 1), sửa đúng node theo fix 1 bước ở trên, rồi chạy lại B5.
