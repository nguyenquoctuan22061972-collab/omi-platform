# Product Vision — OMI Platform

## Tầm nhìn
OMI Platform là hệ điều hành vận hành đa kênh cho doanh nghiệp: hợp nhất khách hàng,
hội thoại và bán hàng, tự động hoá bằng workflow + AI agent, do một lớp điều phối
(Orchestrator) quản trị theo quy trình PRD → TechSpec → Code → QA.

## Bài toán
Dữ liệu khách hàng phân mảnh trên nhiều kênh (Messenger, Zalo, Telegram, Email,
Form, Webhook); đội ngũ mất dấu hội thoại và pipeline; báo cáo thủ công, chậm.

## Người dùng (theo PRD-001)
CEO · Sales · CSKH · Admin.

## Trụ cột sản phẩm
1. **CRM Core** — hồ sơ hợp nhất, timeline, pipeline, KPI (PRD-001, đã build).
2. **Automation (n8n)** — ingest, auto-tag/routing, đồng bộ báo cáo (placeholder).
3. **AI Layer** — tagging/qualify/assist (điểm cắm, hiện rule-based).
4. **Governance** — CTO Bible, chuẩn, chống trùng lặp.

## Nguyên tắc
Bám PRD · không trùng lặp · mọi thứ qua QA · commit theo module.

## Chỉ số thành công (đề xuất)
- Thời gian merge lead < 1s; tỉ lệ trùng dữ liệu ~0.
- % hội thoại gắn đúng contact = 100%.
- Win rate hiển thị realtime trên dashboard.

## Ngoài phạm vi hiện tại
Frontend app hoàn chỉnh, RBAC, hạ tầng production — cần PRD/TechSpec riêng.
