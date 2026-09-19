# YouTube SEO Bible — OMI Platform (PRD-010 H)

Chuẩn SEO/YouTube. Nguồn code: `libs/youtube/` + `libs/prompts` (category `seo`, `thumbnail`).

## Metadata
- Title ≤ 100 ký tự, hook + từ khoá chính đầu tiêu đề.
- Description ≤ 5000 ký tự: 2 dòng đầu chứa từ khoá + CTA; timestamps; link (affiliate UTM).
- Tags ≤ 15, phủ từ khoá chính/phụ.
- `privacyStatus`: private → review → public/schedule.

## Thumbnail
- Concept từ prompt `thumbnail`; text overlay ngắn, tương phản cao, cảm xúc rõ.
- Bind qua `YouTubeRuntime.bind_thumbnail` (dry-run tới khi có credential).

## Playlist & Schedule
- Map category → playlist env (`YT_PLAYLIST_*`).
- Lịch đăng qua `schedule()` + Content Calendar (priority matrix).

## Quy tắc
Không upload thật ở tầng này (dry-run). Bật khi có `YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN`.
