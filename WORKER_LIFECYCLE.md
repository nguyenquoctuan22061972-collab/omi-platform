# Worker Lifecycle (PRD-013 D)

```
      start()
STARTING ---------> READY <-------------------------+
                     |  dequeue job                  |
                     v                               | job xong / idle
                   BUSY ---- success ---> complete --+
                     |
                     | fail (còn lượt)
                     v
                  RETRYING --- backoff (QueueOrchestrator) --> READY
                     |
                     | lỗi nội bộ không phục hồi
                     v
                   FAILED  --> Supervisor escalate (libs/alerts)

   stop() (graceful) bất kỳ lúc nào -> hoàn tất job đang chạy -> STOPPED
```

| State | Ý nghĩa | Chuyển tiếp |
|---|---|---|
| STARTING | vừa tạo, chưa nhận job | `start()` → READY |
| READY | rảnh, chờ job | dequeue → BUSY; `stop()` → STOPPED |
| BUSY | đang chạy 1 job | success → READY; fail(retry) → RETRYING; hết lượt → READY (job vào DLQ) |
| RETRYING | job lỗi, chờ backoff | promote_ready → READY |
| FAILED | lỗi runtime của worker | Supervisor escalate |
| STOPPED | dừng graceful | kết thúc |

**Graceful shutdown**: `stop()` đặt cờ; `run_once()`/`run_forever()` kết thúc job hiện tại
rồi chuyển STOPPED — không cắt ngang giữa chừng. Mỗi bước phát metrics
(`execution_*`, `workflow_duration_ms`) và audit event (`execution_*`).
