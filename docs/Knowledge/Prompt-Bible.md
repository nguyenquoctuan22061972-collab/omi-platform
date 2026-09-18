# Prompt Bible — OMI Platform (PRD-009 H)

Chuẩn prompt. Nguồn: `libs/prompts/registry.py` (version hoá).

## 8 loại
| Category | Dùng cho |
|---|---|
| youtube_long | kịch bản video dài |
| shorts | YouTube Shorts <60s |
| tiktok | TikTok trend |
| facebook | post Facebook |
| seo | tiêu đề/mô tả/tags |
| thumbnail | concept thumbnail |
| veo3 | prompt sinh video Veo3 |
| vertex | prompt tối ưu Vertex |

## Quy tắc version
- v1 = mặc định trong registry. Sửa/cải tiến → `add_version()` (tăng số), **không sửa version cũ**.
- Render: `PromptRegistry().render("<category>", topic="...")`.
- Không nhúng secret/PII vào prompt.

## Best practice
Hook rõ, cấu trúc nhất quán, CTA cụ thể; ghi rõ input/output cho provider (AI Router).
