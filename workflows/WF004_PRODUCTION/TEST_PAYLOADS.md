# WF004 — TEST PAYLOADS

Test URL (khi bấm "Listen for test event"): `/webhook-test/<id>`
Production URL (sau Activate): `/webhook/wf004-call-intelligence`

## 1. Hợp lệ — audio_url
```json
{ "audio_url": "https://example.com/sample-call.wav",
  "contact": { "phone": "+84900000000", "email": "test@omi.local" },
  "lang": "vi-VN" }
```
Kỳ vọng: chạy hết chuỗi tới Metrics.

## 2. Hợp lệ — thêm text/transcript sẵn (bỏ qua STT nếu Anh mở rộng sau)
```json
{ "audio_url": "https://example.com/sample-call.wav",
  "contact": { "email": "lead@omi.local" },
  "lang": "vi-VN",
  "text": "Khách hỏi giá gói Premium và thời gian giao hàng." }
```

## 3. Lỗi — thiếu audio_url (kỳ vọng Validation ném lỗi, dừng)
```json
{ "contact": { "phone": "+84900000000" }, "lang": "vi-VN" }
```
Kỳ vọng: node Validation FAIL "WF004: thiếu audio_url".

## 4. Lỗi — thiếu contact (kỳ vọng dừng)
```json
{ "audio_url": "https://example.com/sample-call.wav" }
```
Kỳ vọng: "WF004: thiếu contact.phone/email".
