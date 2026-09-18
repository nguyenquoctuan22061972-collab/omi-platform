# RISKS — Ghi chú rủi ro (OMI Platform · Deliverable #1)

| # | Rủi ro | Mức | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|---|
| R1 | Repo OMI chưa được tạo trên GitHub (App thiếu quyền tạo repo) | Cao | Chưa push được lên remote | Anh tạo repo `omi-platform` thủ công rồi push bundle này; xem STATUS.md |
| R2 | Chưa có PRD/Tech Spec cho module | Cao | Không được viết code (luật #1,#2) | Placeholder + template sẵn; làm PRD trước |
| R3 | Trùng lặp chức năng giữa agent/module | TB | Lãng phí, khó bảo trì | Bắt buộc tra CTO-Bible/capability-map.md |
| R4 | Lộ secret khi commit | Cao | Rò rỉ tài khoản/kênh | Không commit secret; env/secret manager; nhắc trong Security/ |
| R5 | Nền tảng bên thứ ba khóa kênh | Cao | Mất kênh/doanh thu | SOP incident; tuân thủ chính sách; sao lưu tài sản |
| R6 | Nghẽn do chờ duyệt PRD/Tech Spec | TB | Chậm tiến độ | Quy trình duyệt rõ; ưu tiên module trọng điểm |
| R7 | Chi phí & điều phối nhiều AI Agent | TB | Tốn token, khó quản | Bắt đầu nhỏ, mở rộng theo capability-map |

> Cập nhật mỗi khi phát sinh/đóng rủi ro.
