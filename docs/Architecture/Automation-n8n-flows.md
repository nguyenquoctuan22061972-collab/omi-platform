# Automation n8n — Sequence & Data-flow (PRD-003)

## 1. Sequence — WF001 Lead Ingestion
```mermaid
sequenceDiagram
    participant CH as Kênh (FB/Zalo/TG/Email/Form/API)
    participant N as n8n WF001
    participant CRM as CRM Core API
    CH->>N: POST /webhook/crm/lead {payload}
    N->>N: (disabled) Verify Signature
    N->>N: Normalize → {name,phone,email,channel,message}
    N->>CRM: POST /contacts {name,phone,email,source}
    CRM-->>N: 201 {contact.id}  (merge nếu trùng phone/email)
    N->>CRM: POST /messages {contact_id,channel,message}
    CRM-->>N: 201 {conversation}
    N-->>CH: 200 {ok:true}
```

## 2. Sequence — WF002 Auto-Tag & Routing
```mermaid
sequenceDiagram
    participant SRC as Trigger (new conversation)
    participant N as n8n WF002
    participant CRM as CRM Core API
    participant S as Sales/CSKH (Slack, disabled)
    SRC->>N: POST /webhook/crm/new-conversation
    N->>N: Suggest Tags (rule-based)
    N->>CRM: POST /contacts {phone,email,tags}  (merge tags)
    CRM-->>N: 200 {contact}
    N->>N: Route (switch theo tag)
    N-->>S: (disabled) Notify Sales/CSKH
```

## 3. Sequence — WF050 KPI Sync
```mermaid
sequenceDiagram
    participant T as Schedule (cron)
    participant N as n8n WF050
    participant CRM as CRM Core API
    participant R as Report sink (Email, disabled)
    T->>N: tick
    N->>CRM: GET /dashboard/kpi  (GAP: chưa có endpoint)
    CRM-->>N: {total_contacts,total_messages,win_rate,...}
    N->>N: Format
    N-->>R: (disabled) Send Report
```

## 4. Data-flow tổng
```
[6 Kênh] --payload--> (WF001 normalize) --> [CRM: contacts/conversations]
                                   |
              (WF002) tag+route <--+--> [CRM: contacts.tags] --> [Sales/CSKH]
                                   |
              (WF050) <----- cron -+--> [CRM: kpi] --> [Report]
```

## 5. Hợp đồng dữ liệu (data contract)
| Bước | Trường | Nguồn |
|---|---|---|
| Ingest | name, phone, email, channel, message | payload kênh |
| Contact | id, source, tags | CRM `/contacts` |
| Conversation | contact_id, channel, message, timestamp | CRM `/messages` |
| KPI | total_contacts, total_messages, win_rate | CRM `/dashboard/kpi` (gap) |

## 6. Ranh giới lỗi (fault boundary)
Mỗi HTTP node là 1 ranh giới: lỗi được cô lập, không làm hỏng cả run (Continue On
Fail) → nhánh error/retry (xem runbook).
