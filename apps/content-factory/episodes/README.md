# Episode Factory — Script → Voice → Video → QA (10 kênh, 1 engine)

Một engine sản xuất, dùng chung cho cả 10 kênh (đổi brand/handle/màu theo preset ở
`libs/video/channels.py`). Mỗi tập: tải ảnh (đa nguồn, fallback) → (tùy chọn) lồng tiếng
→ render MP4 thật (Ken Burns + crossfade + nhạc nền, ducking khi có voice) → `.srt` +
thumbnail riêng → metadata YouTube **DRY-RUN**. KHÔNG tự publish.

## Lệnh
```bash
# liệt kê kênh
python apps/content-factory/episodes/produce.py --list

# kiểm tra nguồn ảnh
python apps/content-factory/episodes/produce.py --channel finance --probe-only

# sản xuất 1 tập cho 1 kênh (dùng chung engine)
python apps/content-factory/episodes/produce.py --channel heartrise --ep 1
python apps/content-factory/episodes/produce.py --channel finance  --ep 1 --no-voice
```
Output: `build/<kênh>_ep01/` gồm MP4 + `.srt` + `thumbnail.png` + `manifest.json`
(đã `.gitignore`).

## Lồng tiếng (voiceover)
Bật tự động theo biến môi trường (xem `libs/video/narration.py`):
- `NARRATION_FILE=<path>` — dùng file đọc có sẵn (vd xuất từ ElevenLabs).
- `ELEVENLABS_API_KEY` + `ELEVEN_VOICE_ID` — gọi ElevenLabs REST (TTS) trực tiếp.
- Không có → chạy nhạc nền (không voice), pipeline vẫn hoàn tất.

## Thành phần
| File | Vai trò |
|---|---|
| `script.py` | Sinh kịch bản template (offline, deterministic) + chỗ nối LLM. |
| `factory.py` | Orchestrator `make_episode`: tải→voice→render→srt→thumb→QA→metadata. |
| `produce.py` | CLI `--channel` dùng chung cho mọi kênh. |
| `heartrise_ep01/` | Kịch bản bespoke tập mở màn HeartRise. |

## Nối vào hệ thống
- **Pipeline**: `apps/content-factory/pipeline/video_runner.py` map stage `video`/`thumbnail`
  /`qa`/`publish` của `ContentPipeline` sang engine thật (render=True) — không sửa pipeline lõi.
- **Lịch hàng loạt**: `apps/content-factory/calendar/scheduler.py` nối `ContentCalendar`
  → `JobQueue` (seed tuần + đẩy job `render_episode`).

## QA
```bash
cd apps/content-factory/episodes && python -m unittest discover -s tests -p 'test_*.py'
```
