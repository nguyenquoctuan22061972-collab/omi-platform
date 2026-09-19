# Queue Strategy (PRD-013 B)

Tái dùng `apps/content-factory/queue/jobqueue.py` (priority heap + dead-letter). Lớp
`QueueOrchestrator` thêm **exponential backoff** và **đo lường** — không sửa hàng đợi gốc.

## Priority
- `priority` nhỏ hơn = ưu tiên cao hơn (min-heap). Tie-break theo thứ tự nạp (FIFO ổn định).

## Retry + Exponential Backoff
```
delay = min(base_backoff_s * 2^(attempt-1), max_backoff_s)

attempt 1 lỗi -> delay = base * 1
attempt 2 lỗi -> delay = base * 2
attempt 3 lỗi -> delay = base * 4
...
```
- Job lỗi (còn lượt) **không** vào heap ngay: giữ ở `_delayed` với mốc `ready_at`.
- `promote_ready(now)` đưa job đủ hạn trở lại heap (được gọi tự động mỗi `dequeue`/`tick`).

## Dead-Letter Queue (DLQ)
- Hết `max_retries` → dùng `JobQueue.fail` sẵn có để đẩy vào `dead_letter` (không mất dấu).
- `stats()` báo `dead_letter`, `delayed`, `retry_count`, `depth`.

## Metrics
- `queue_size` = depth (heap chờ + delayed backoff).
- `retry_count` = tổng lần retry — expose qua `libs/metrics` collectors (`metrics_snapshot()`).
