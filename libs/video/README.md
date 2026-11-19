# libs/video — Render MP4 thực tế (PRD-009 E)

Biến stage **"video"** của `apps/content-factory/pipeline` từ mock → MP4 thật. **Additive**:
lib mới, không sửa module cũ; pipeline dùng qua `runner` injectable sẵn có.

## Thành phần
| File | Vai trò |
|---|---|
| `sources.py` | Registry 3 nguồn ảnh miễn phí (Pexels/Unsplash/Pixabay CDN) + probe khả năng tải + `download_first` fallback khi một domain bị chặn. Chỉ CDN công khai, không cần API key. |
| `renderer.py` | `VideoRenderer`: PIL dựng khung cảnh (chữ tiếng Việt, branding) + ffmpeg Ken Burns & crossfade + numpy tổng hợp nhạc nền ambient → MP4 (H.264/AAC). |

## Nguyên tắc
- **PIL/numpy nạp lazy** → môi trường CI không cài vẫn import được; test render tự **SKIP**.
- **Fallback nguồn**: domain bị chặn → tự chuyển nguồn còn truy cập được (báo rõ domain).
- **Không gọi API khi render**: asset tải về trước; render thuần offline.
- **Không tự publish**: upload YouTube vẫn dry-run ở `libs/youtube`.

## Test
```bash
cd libs/video && python -m unittest discover -s tests -p 'test_*.py'
# test mạng thật (tùy chọn):
VIDEO_NET_TESTS=1 python -m unittest discover -s tests -p 'test_*.py'
```

## Rủi ro
- Một domain nguồn có thể bị WAF/proxy chặn (trang gốc 403) — đã xử lý bằng probe nhắm
  asset thật + fallback đa nguồn.
- Chưa có lồng tiếng (TTS) — xem phần "còn thiếu" trong episode.
