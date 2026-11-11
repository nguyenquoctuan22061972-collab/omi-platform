# Content Factory · Video Renderer

Dựng MP4 16:9 1080p từ **ảnh cảnh + giọng đọc + phụ đề**, chạy hoàn toàn trên cloud (không cần máy Windows/CapCut).

## Dây chuyền một tập

```
Ý tưởng (vidIQ) → Tiêu đề → Kịch bản VO (Claude) → Giọng đọc (ElevenLabs)
→ Mốc thời gian từng từ (ElevenLabs speech-to-text, miễn phí)
→ Ảnh cảnh (ElevenLabs / Canva, giữ nhân vật qua ảnh tham chiếu)
→ render.py: Ken Burns + phụ đề + ghép → MP4 → duyệt trên điện thoại → YouTube
```

## Cấu trúc một tập

```
episodes/<tap>/
  episode.json   # slug, kênh, tiêu đề, nhân vật, danh sách cảnh (start giây + ảnh + prompt), fallback
  script.txt     # kịch bản VO
  vo.mp3         # giọng đọc            (không commit)
  words.json     # {"words": [{text,type,start,end}]}  (không commit)
  img/sNN.png    # ảnh từng cảnh        (không commit)
  out/           # MP4 thành phẩm       (không commit)
```

`scenes[].start` lấy từ `words.json` (giây bắt đầu của câu mở cảnh).
`fallback` cho phép dựng bản xem trước khi chưa đủ ảnh.

## Chạy

```bash
python3 render.py episodes/heartrise-ep01 --preview 60   # 60 giây đầu
python3 render.py episodes/heartrise-ep01                # bản đầy đủ
```

Cần `ffmpeg` có libass (phụ đề) và font DejaVu.

## Mạng cần mở cho môi trường cloud

| Tên miền | Dùng cho |
|---|---|
| `storage.googleapis.com` | Tải giọng/ảnh từ ElevenLabs (đang hoạt động) |
| `media.canva.com`, `www.canva.com`, `export-download.canva.com` | Tải ảnh AI tạo bằng Canva |
| `videos.pexels.com`, `images.pexels.com`, `api.pexels.com` | Video/ảnh stock miễn phí (Pexels) |
| `pixabay.com`, `cdn.pixabay.com` | Ảnh, video, nhạc nền miễn phí (Pixabay) |
| `images.unsplash.com`, `api.unsplash.com` | Ảnh miễn phí (Unsplash) |
| `assets.mixkit.co` | Clip + nhạc nền miễn phí (Mixkit) |
| `upload.wikimedia.org` | Ảnh tư liệu lịch sử (Wikimedia Commons) |

Ghi công tác giả stock trong mô tả video. Video AI trông như thật: bật nhãn “nội dung đã chỉnh sửa/tổng hợp” khi đăng YouTube.
