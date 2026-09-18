# TESTPLAN — QA cho OMI Platform

Luật #3: **mọi file đều phải qua QA.**

## 1. QA tài liệu
- [ ] Đúng template (PRD đủ 11 mục; TechSpec đủ mục bắt buộc)
- [ ] Không link chết
- [ ] Không lộ secret (key/token/mật khẩu)
- [ ] Nhất quán với CTO-Bible/standards.md

## 2. QA code (khi có)
- [ ] Có PRD + Tech Spec tham chiếu (không có → FAIL, không merge)
- [ ] Unit test cho logic chính; bám "Test Case" trong PRD
- [ ] Không trùng chức năng (capability-map.md)
- [ ] Lint/format sạch

## 3. Kiểm thử scaffold (Deliverable #1)
```bash
find . -type d | sort            # đủ cây thư mục
find . -type d -empty            # kỳ vọng: KHÔNG in gì (không dir rỗng)
```
Kỳ vọng: mọi thư mục có README; PRD & TechSpec có _TEMPLATE.md.

## Định nghĩa "Done"
Đủ 4 output (File · Checklist · Test · Risk) và pass QA tương ứng.
