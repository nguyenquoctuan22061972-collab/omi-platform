# Workflow Bible — OMI Platform (PRD-009 H)

Tổng quan mọi workflow n8n. Nguồn sự thật: `workflows/runtime/registry.py`.

| WF | Tên | Version | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| WF001 | Lead Ingestion | 1.0 | CRM Core | importable |
| WF002 | AI Auto-Tag & Routing | 1.0 | WF001, CRM Core | importable |
| WF003 | Content Publish (future) | 0.0 | content-factory | planned |
| WF050 | Dashboard KPI Sync | 1.0 | CRM Core (CR-001) | importable |

## Quy tắc
- Không sửa workflow business đã có; thêm workflow mới = thêm thư mục `WFxxx/` + đăng ký registry.
- Bật production theo `deploy/n8n/enable-production.md`; rollback theo `deploy/n8n/rollback.md`.
- Validate runtime: `python3 workflows/runtime/validate.py`; registry: `workflows/runtime/registry.py`.

## Rollback mapping
Mặc định: re-import bản Git trước (mỗi workflow versioned trong Git).
