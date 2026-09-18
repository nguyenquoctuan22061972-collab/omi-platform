# ADR-0002 — Automation bằng n8n (workflow-as-code)

- **Trạng thái:** Accepted (cho scope B)
- **Ngày:** 2026-09-18
- **Liên quan:** PRD-003, TechSpec Automation-n8n

## Bối cảnh
Cần tự động hoá luồng CRM đa kênh (PRD-001 §9). Có thể viết service tuỳ biến hoặc
dùng nền tảng workflow. Bối cảnh dự án đã hướng n8n (repo gốc là n8n-docs).

## Quyết định
Dùng **n8n**, quản lý **workflow-as-code** (JSON versioned trong Git). n8n gọi CRM
Core REST API; state ở CRM Core. Credential quản trong n8n, không nằm trong repo.

## Lý do
- Tốc độ: kéo-thả, nhiều connector sẵn cho FB/Zalo/Telegram/Email.
- Tách biệt: logic nghiệp vụ CRM ở PRD-001; n8n chỉ orchestrate → ít trùng lặp (luật #4).
- Versioned JSON trong Git → review, diff, rollback dễ.

## Hệ quả
- ➕ Triển khai nhanh, dễ mở rộng workflow.
- ➖ Phụ thuộc runtime n8n + credential ngoài → không test "thật" offline (scope B chỉ
  validate JSON tĩnh).
- **Ràng buộc:** node cần secret để `disabled` trong JSON commit; bật khi gắn credential.

## Thay thế đã cân nhắc
Service automation tự viết (Python) — kiểm soát tốt hơn nhưng chậm, trùng công dụng
n8n, tốn bảo trì. Hoãn trừ khi n8n không đáp ứng.
