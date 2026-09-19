# Revenue Playbook — OMI Platform (PRD-010 H)

Cách kiếm tiền & đo lường. Nguồn code: `apps/revenue-engine/` + `libs/affiliate` + `libs/analytics`.

## Nguồn doanh thu
| Nguồn | Cơ chế | Module |
|---|---|---|
| Affiliate | click → conversion → hoa hồng | `libs/affiliate` + revenue-engine click pipeline |
| Lead | lead → CRM → chốt deal | `libs/lead` + CRM Core |
| Ads (RPM) | views × RPM (placeholder) | revenue-engine (chờ dữ liệu views) |

## Vòng đo lường
```
click (analytics) → conversion (ConversionTracker) → revenue (RevenueRegistry) → dispatch (EventDispatcher)
attribution theo campaign (analytics) → overview/monthly trend (revenue-engine)
```

## Quy tắc
- Không thanh toán/payout thật ở tầng này (PayoutAbstraction dry-run).
- RPM/AI cost là placeholder tới khi có nguồn dữ liệu thật.
- Mọi kết nối thật đọc từ env, sau adapter flag.

## KPI điều hành
Today's Revenue · Pipeline Value · Affiliate Clicks · CVR · Monthly trend — hiển thị
qua CEO Revenue Dashboard (`apps/ceo-autopilot/src/revenue_dashboard.py`).
