# Rollback Decision Tree — OMI Platform (PRD-006 F)

```
Sự cố sau deploy?
├─ CI đỏ / smoke fail ngay
│   └─> Rollback image về tag trước (Deploy manual) → healthcheck
├─ App lỗi nhưng dữ liệu nguyên vẹn
│   ├─ Lỗi cấu hình (.env) → sửa .env → up -d (không cần rollback image)
│   └─ Lỗi code → rollback image tag trước
├─ Dữ liệu hỏng / migration sai
│   └─> restore.sh backup gần nhất → up -d → healthcheck
└─ Chỉ 1 workflow n8n lỗi
    └─> tắt workflow đó, re-import bản Git trước (không đụng service khác)
```

## Nguyên tắc
- **Ưu tiên khôi phục dịch vụ** trước, tìm căn nguyên sau.
- Rollback theo **image tag** (immutable), không sửa tay trên prod.
- Dữ liệu: chỉ restore khi xác định corrupt (tránh mất data mới hơn).
- Mọi rollback ghi lại (thời điểm, tag, lý do) cho postmortem.

## Tiêu chí quyết định restore dữ liệu
Restore khi: mất/hong dữ liệu xác nhận. KHÔNG restore khi: chỉ lỗi app/config (mất data
mới là cái giá không cần thiết).
