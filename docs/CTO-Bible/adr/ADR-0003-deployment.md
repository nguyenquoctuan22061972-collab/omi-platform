# ADR-0003 — Production Deployment: Docker Compose + Nginx + GitHub Actions

- **Trạng thái:** Accepted
- **Ngày:** 2026-09-18
- **Liên quan:** PRD-005

## Bối cảnh
Cần đưa OMI Platform (CRM Core, Auth, Dashboard, Automation) lên production mà không
sửa business logic PRD-001..004.

## Quyết định
- **Docker Compose** cho orchestration (đơn giản, đủ cho quy mô hiện tại).
- **Nginx** reverse proxy + SSL (Let's Encrypt) + rate limit + CSP/headers.
- **GitHub Actions**: CI (build/test) tự động; deploy **thủ công** (workflow_dispatch +
  Environment approval) để tránh sự cố.
- **SQLite trên volume** (giữ nguyên stack ứng dụng, ADR-0001) + backup/restore script.

## Lý do
- Không phải rewrite app (đúng "không redesign").
- Compose đủ nhẹ; nâng lên Kubernetes sau nếu quy mô tăng.
- Deploy thủ công giảm rủi ro auto-deploy hỏng.

## Hệ quả
- ➕ Lên production nhanh, chi phí thấp, dễ rollback theo image tag.
- ➖ SQLite giới hạn concurrency/HA → khi tải cao chuyển Postgres (ADR mới) + tách DB.
- Backup dựa trên volume tar; cần test restore định kỳ (DR).

## Thay thế đã cân nhắc
Kubernetes (thừa cho quy mô hiện tại) · PaaS (khoá nhà cung cấp) — hoãn.
