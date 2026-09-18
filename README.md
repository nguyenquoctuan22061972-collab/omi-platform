# OMI Platform — CTO Documentation Foundation

> Dự án **CEO Quốc Tuấn – OMI Platform**. Repo này chứa **Deliverable #1: Nền tảng
> tài liệu CTO**, vận hành theo mô hình **Master Orchestrator điều phối AI Agent**.

## Nguyên tắc điều phối (Governance — bắt buộc)

1. **Không tạo kiến trúc mới nếu chưa có Tech Spec.**
2. **Mọi code phải bám PRD.**
3. **Mọi file đều phải qua QA.** (xem `TESTPLAN.md` + `docs/QA/`)
4. **Không trùng lặp chức năng.** (tra `docs/CTO-Bible/` trước khi thêm mới)
5. **Commit theo module.**

> Phiên tạo Deliverable #1 chỉ tạo **tài liệu**, **không tạo code** (đúng luật).

## Output chuẩn mỗi hạng mục

1. **File** — 2. **Checklist** — 3. **Test** — 4. **Ghi chú rủi ro**

## Cấu trúc repo

```
docs/
├── PRD/          # Product Requirement Documents — nguồn sự thật cho code
├── TechSpec/     # Tech Spec — bắt buộc trước khi dựng kiến trúc
├── SOP/          # Quy trình vận hành chuẩn
├── API/          # Hợp đồng API giữa các module
├── CTO-Bible/    # Quyết định kỹ thuật (ADR), chuẩn chung, chống trùng lặp
├── Architecture/ # Kiến trúc hệ thống (diagram, bối cảnh, thành phần)
├── Database/     # Mô hình dữ liệu, schema, migration
├── Security/     # Bảo mật, phân quyền, secrets, tuân thủ
├── QA/           # Chiến lược & kịch bản kiểm thử
├── Deployment/   # CI/CD, môi trường, quy trình release
├── Operations/   # Vận hành, giám sát, incident, on-call
├── Product/      # Tầm nhìn sản phẩm, personas, tính năng
├── Research/     # Nghiên cứu thị trường, đối thủ, nền tảng
└── Roadmap/      # Lộ trình theo quý/mốc
workflows/        # WF001, WF002, WF050 — automation (placeholder)
ai/
├── prompts/      # Thư viện prompt
├── agents/       # Định nghĩa agent
└── skills/       # Skill dùng lại được
```

## Trạng thái

Deliverable #1 = scaffold + README từng thư mục + template PRD/TechSpec + QA
checklist + test plan + risk notes. Chi tiết ở `STATUS.md`.
