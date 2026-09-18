# Runbook — Automation n8n (PRD-003)

Vận hành 3 workflow WF001/WF002/WF050. Áp dụng khi go-live (sau khi gắn credential).

## 1. Error handling
| Loại lỗi | Xử lý |
|---|---|
| 4xx từ CRM (vd 400 stage sai) | Không retry; ghi nhánh error → alert; sửa payload |
| 5xx / timeout CRM | Retry (xem §2) |
| Node cần credential nhưng disabled | Bật node + gắn credential; không bypass |
| Webhook payload sai định dạng | `Normalize` set mặc định; nếu thiếu định danh → trả 200 + log skip |

Nguyên tắc: mỗi HTTP node bật **Continue On Fail** để cô lập lỗi; nhánh lỗi đi tới
node alert (Slack/Email — disabled tới khi có credential).

## 2. Retry
- HTTP node: `Retry On Fail = true`, `Max Tries = 3`, `Wait Between Tries` backoff:
  **1s → 4s → 9s** (luỹ thừa nhẹ).
- Chỉ retry lỗi tạm thời (5xx, timeout, ECONNRESET). Lỗi 4xx **không** retry.
- **Idempotency:** CRM merge theo `phone|email` → gọi lại `POST /contacts` an toàn,
  không tạo trùng. `POST /messages` gắn `contact_id` → tránh lạc contact.

## 3. Logging
- **Execution log n8n:** bật lưu execution (success + error) để truy vết.
- **Business audit:** đẩy sự kiện tag/route về CRM `audit_logs` (PRD-002) khi tích hợp.
- **Không log secret/PII thô.** Che số điện thoại/email trong log tuỳ chính sách.
- Mức log: INFO (bước chính), WARN (retry), ERROR (thất bại sau max tries).

## 4. Rollback
1. Xác định workflow lỗi (WFxxx) qua Executions.
2. **Tắt** workflow lỗi (Active → off) để dừng thiệt hại.
3. `git checkout <commit_tốt> -- workflows/WFxxx/workflow.json`.
4. Re-import JSON phiên bản tốt vào n8n (Import from File, overwrite).
5. Bật lại; theo dõi 10 execution kế tiếp.
> Vì workflow versioned trong Git, rollback = re-import bản Git trước. Không sửa tay
> trên n8n production mà không commit lại (tránh lệch nguồn).

## 5. Monitoring / Alert
- Theo dõi tỉ lệ execution failed; ngưỡng cảnh báo > 5%/giờ.
- Alert qua node Slack/Email (bật khi có credential).

## 6. Go-live checklist
- [ ] Đặt `N8N_BASE_URL`, `CRM_BASE`.
- [ ] Gắn credential mỗi kênh + kênh notify.
- [ ] Bật các node `disabled`.
- [ ] Bổ sung `GET /dashboard/kpi` cho CRM Core (gap) trước khi bật WF050.
- [ ] Bật Retry/Continue-On-Fail theo §1-§2.
- [ ] Kiểm tra Executions sạch lỗi.
