# HeartRise Stories — TẬP 01: "Ngày Con Tim Thức Dậy"

Episode mở màn kênh #1 (`@HeartRiseStories`, niche Cảm hứng). Sinh **MP4 thật** 1920×1080,
~62s, H.264/AAC, 8 cảnh, Ken Burns + crossfade + nhạc nền ambient gốc.

## Build
```bash
# chỉ kiểm tra nguồn ảnh (Pexels/Unsplash/Pixabay)
python apps/content-factory/episodes/heartrise_ep01/build.py --probe-only

# render MP4 đầy đủ
python apps/content-factory/episodes/heartrise_ep01/build.py
# → build/HeartRise_EP01.mp4  +  build/manifest.json
```
Output nằm trong `build/` (đã `.gitignore` — không commit binary nặng).

## Luồng (đúng yêu cầu vận hành)
1. Probe 3 nguồn → báo domain truy cập được / bị chặn.
2. Tải asset theo cảnh, **fallback đa nguồn** nếu một domain bị chặn.
3. Render MP4 thật (không chỉ prompt/kế hoạch).
4. Metadata YouTube **DRY-RUN** — KHÔNG tự động publish.

## File
| File | Vai trò |
|---|---|
| `storyboard.py` | Kịch bản 8 cảnh (tiếng Việt) + URL asset đa nguồn đã kiểm chứng + metadata YouTube. |
| `build.py` | Orchestrate probe → tải → render → dry-run metadata → `manifest.json`. |

## Test
```bash
cd apps/content-factory/episodes/heartrise_ep01
python -m unittest discover -s tests -p 'test_*.py'
```

## Còn thiếu / nâng cấp tiếp
- **Lồng tiếng (voiceover)**: container chưa có TTS offline. `VideoRenderer` đã sẵn sàng
  mux audio — chỉ cần đưa file narration (vd ElevenLabs) vào để nâng cấp.
- Phụ đề (.srt) khớp timeline từng cảnh.
- Thumbnail riêng (hiện dùng khung intro).
