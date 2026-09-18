# ADR-0001 — Stack cho CRM Core

- **Trạng thái:** Accepted
- **Ngày:** 2026-09-18
- **Liên quan:** PRD-001, TechSpec CRM-Core

## Bối cảnh
Cần hiện thực CRM Core (PRD-001) chạy được và QA offline trong môi trường session
(mạng qua proxy, không chắc cài được dependency).

## Quyết định
Dùng **Python 3.11 stdlib**: `sqlite3` (DB), `http.server` (REST), `unittest` (QA).
Server chạy **đơn luồng** (`HTTPServer`) + `check_same_thread=False`.

## Lý do
- Không phụ thuộc mạng → QA chạy được ngay, ổn định.
- Đủ cho MVP đúng phạm vi PRD-001 (5 endpoint, 3 bảng).
- Đơn luồng loại bỏ lỗi SQLite cross-thread (đã gặp với `ThreadingHTTPServer`).

## Hệ quả
- ➕ Khởi động nhanh, dễ test, ít rủi ro build.
- ➖ Không chịu tải cao / concurrency thật.
- **Đường nâng cấp:** khi có TechSpec Deployment → chuyển sang ASGI (FastAPI/uvicorn)
  + Postgres, giữ nguyên hợp đồng API §6. Rate-limit & RBAC bổ sung ở bước đó.

## Thay thế đã cân nhắc
FastAPI + Postgres (mạnh hơn nhưng cần cài đặt/mạng — hoãn tới Deployment).
