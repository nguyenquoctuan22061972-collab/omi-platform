# Affiliate Bible — OMI Platform (PRD-010 H)

Chuẩn affiliate. Nguồn code: `libs/affiliate/`.

## Networks
AccessTrade · Shopee · Amazon · TikTok Shop · Custom Partner.

## Cấu hình
- Tracking id qua env `<NET>_TRACKING_ID` (không hardcode).
- Link chiến dịch: `AffiliateRegistry.campaign_link(network, url, campaign)` → gắn UTM + deep-link (abstraction).

## UTM chuẩn
`utm_source=<network>` · `utm_medium=affiliate` · `utm_campaign=<campaign>`.

## Quy tắc
- Deep-link chỉ "ready" khi có tracking id.
- Không gọi API rút gọn thật ở tầng này (service dựng URL khi go-live).
- Đo hiệu quả qua `libs/analytics` (attribution theo campaign) + `apps/revenue-engine` (click pipeline).
