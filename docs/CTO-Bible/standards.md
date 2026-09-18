# Engineering Standards — OMI Platform

Chuẩn kỹ thuật chung. Áp dụng cho mọi module & agent (luật Orchestrator).

## 1. Vòng đời (bắt buộc theo thứ tự)
`Research → Product → PRD → Architecture/DB/Security → TechSpec → Code → QA → Deployment → Operations`
Không nhảy bước. Không code khi PRD/TechSpec chưa duyệt.

## 2. Đặt tên
- PRD: `docs/PRD/PRD-<nnn>.md` (nội dung) — mã tăng dần.
- TechSpec: `docs/TechSpec/<Module>.md`.
- App/service: `apps/<module>/` (snake/kebab, số ít).
- Test: `tests/test_<chủ_đề>.py`.

## 3. Commit (luật #5 — commit theo module)
```
<type>(<module>): <mô tả ngắn, tiếng Việt được>
```
`type` ∈ feat · fix · docs · test · refactor · chore · perf · ci.
Mỗi commit gói **1 module / 1 mục đích**. Không trộn nhiều module trong 1 commit.

## 4. Code
- Ngôn ngữ mặc định lõi hiện tại: **Python 3.11** (stdlib-first cho MVP; thêm dependency phải ghi ở TechSpec).
- Tham số hoá truy vấn SQL (chống injection).
- Hàm public có docstring nêu input/output.
- Không commit secret; cấu hình qua biến môi trường.

## 5. QA (luật #3)
- Mọi module có test tự động map tới "Test Case" trong PRD.
- Định nghĩa Done: **File · Checklist · Test · Risk notes** + test PASS.
- Có smoke test cho tầng API.

## 6. Chống trùng lặp (luật #4)
Trước khi thêm chức năng → tra `capability-map.md`. Nếu đã có, tái sử dụng.

## 7. Tài liệu khớp code
Schema/API doc phải khớp 1-1 với code. Đổi code → cập nhật doc cùng commit/PR.
