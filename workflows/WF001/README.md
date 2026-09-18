# WF001 — Lead Ingestion (n8n) · PLACEHOLDER

**Trạng thái:** 🟡 Placeholder — chưa nối credential/deploy.
**Map PRD-001 §9:** bước 1 (Lead vào từ nhiều kênh) + bước 2 (Merge theo phone/email).

## Luồng n8n (dự kiến)
```
[Webhook: FB/Zalo/Telegram/Email/Form/API]
        → [Function: normalize payload → {name,phone,email,channel,message}]
        → [HTTP Request: POST /contacts]      (CRM Core tự merge §9.2)
        → [HTTP Request: POST /messages]
        → [Respond to Webhook 200]
```

## Input (6 kênh — PRD §4)
facebook_messenger · zalo_oa · telegram · email · form_landing_page · api_webhook

## Output
Contact hợp nhất + 1 conversation gắn đúng contact.

## Điều kiện triển khai
Cần TechSpec workflow riêng + credential từng kênh (giai đoạn Deployment). Xem
`workflow.json` (skeleton placeholder, chưa chạy được).
