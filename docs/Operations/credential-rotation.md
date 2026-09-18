# Credential Rotation — OMI Platform (PRD-006 F)

Xoay định kỳ (khuyến nghị 90 ngày) hoặc ngay khi nghi lộ.

## Danh mục & cách xoay
| Credential | Nơi lưu | Cách xoay | Ảnh hưởng |
|---|---|---|---|
| `AUTH_SECRET` (JWT) | deploy/.env | sinh mới (`openssl rand -hex 32`) → restart auth-rbac | **Tất cả token cũ hết hiệu lực** → user re-login |
| Channel tokens (Telegram/Zalo/FB) | n8n credential + env | tạo token mới ở provider → cập nhật → bật lại node | gián đoạn kênh đó tạm thời |
| SMTP pass | env/n8n | đổi ở nhà cung cấp → cập nhật | email tạm dừng |
| OpenAI/Vertex key | env/secret store | tạo key mới → thay → thu hồi key cũ | tác vụ AI tạm dừng |
| Deploy SSH key | GitHub Environment secret | tạo cặp mới → cập nhật server authorized_keys + secret | — |

## Quy trình chuẩn
1. Tạo credential mới (không xoá cũ ngay).
2. Cập nhật `.env`/secret store/n8n.
3. Reload service liên quan.
4. Xác minh healthcheck + chức năng.
5. **Thu hồi** credential cũ.
6. Ghi nhật ký xoay (ngày, ai, cái gì).

## Lưu ý
- Không commit secret. Chỉ `.env.example` trong repo.
- Xoay `AUTH_SECRET` nên báo trước (user phải đăng nhập lại).
