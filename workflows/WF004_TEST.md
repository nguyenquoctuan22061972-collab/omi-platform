# WF004 — AI Call Intelligence · Test Plan (WO-015)

## Static QA (tự động — `workflows/tests/test_wf004.py`, 9 test, PASS)
| TC | Kiểm tra | Kết quả |
|---|---|---|
| TC1 | JSON hợp lệ, import được (name/nodes/connections) | ✅ |
| TC2 | Đủ 8 node pipeline | ✅ |
| TC3 | Có webhook trigger + httpRequest | ✅ |
| TC4 | Connections trỏ node tồn tại | ✅ |
| TC5 | Đúng thứ tự chuỗi Webhook→…→Metrics | ✅ |
| TC6 | URL http đều dùng `$env.` (không hardcode host) | ✅ |
| TC7 | CRM/Audit/Metrics dùng `$env.CRM_BASE` | ✅ |
| TC8 | Node có credential đều `disabled` | ✅ |
| TC9 | Không secret literal | ✅ |

Không phá `workflows/tests/test_workflows.py` (vẫn đúng 3 `WF*/workflow.json`).

## Manual/Integration (external — cần credential, ngoài repo)
| TC | Bước | Kỳ vọng |
|---|---|---|
| M1 | Import JSON vào n8n | 8 node, không lỗi parse |
| M2 | POST thiếu `audio_url` | Validation ném lỗi, dừng |
| M3 | POST hợp lệ (đã bật credential) | STT→Summary→CRM conversation mới |
| M4 | Telegram | Nhận tin nhắn summary |
| M5 | Audit + Metrics | CRM /audit có record; /metrics/ingest tăng workflow_count |

## Lệnh chạy static test
```
python3 -m unittest discover -s workflows/tests -p 'test_wf004.py'
```
