# Content Factory Bible — OMI Platform (PRD-010 H)

Vận hành nhà máy nội dung. Nguồn code: `apps/content-factory/` + `libs/prompts` + `libs/ai_router` + `libs/publish`.

## Luồng end-to-end
```
Topic → Research → Script → Thumbnail → Video → QA → Publish   (pipeline state machine)
   │        (Prompt Registry render + AI Router chọn provider)
   └── điều phối bởi Job Queue (priority/retry/dead-letter)
   └── lịch đăng bởi Content Calendar (priority matrix + retry)
   └── xuất bản bởi Publish Connectors (dry-run)
```

## Quy tắc
- Prompt version hoá (`libs/prompts`); không sửa version cũ.
- Provider bật theo env (`libs/ai_router`); mặc định dry-run.
- Calendar: item tới hạn sắp theo priority; retry ≤ 3 rồi failed.
- Mọi bước mock/dry-run tới khi có credential + hiện thực hàm thật (giữ interface).

## Đo lường
Analytics events (funnel/attribution) + Revenue Engine (click→conversion→revenue).
