# Runtime Architecture — OMI Orchestrator (PRD-013)

> Backbone điều phối execution cho hệ 800 AI Agent tương lai. **Additive**: tái dùng
> `libs/metrics`, `libs/audit`, hàng đợi `apps/content-factory/queue`, `libs/alerts`,
> `runtime-health`. KHÔNG đổi PRD001–010 / ADR / capability-map / tên module.

## Thành phần (`orchestrator/runtime/`)
| Lớp | File | Vai trò |
|---|---|---|
| Execution Engine | `execution.py` | Chạy 1 capability với timeout + cancellation, phát metrics/audit |
| Queue Orchestration | `queue_orchestrator.py` | Bọc `JobQueue` (reuse) + exponential backoff + DLQ + retry metric |
| Capability Dispatcher | `dispatcher.py` | lookup + version resolution + fallback + tracing (handler inject) |
| Worker Runtime | `worker.py` | vòng đời worker, graceful shutdown, phát metrics/audit |
| Supervisor Runtime | `supervisor.py` | assign job, retry orchestration, heartbeat, escalation, health |

## Luồng dữ liệu

```
                 +---------------------+
   enqueue  -->  |  QueueOrchestrator  |  (reuse JobQueue: priority heap + DLQ)
                 |  + backoff + retry  |
                 +----------+----------+
                            | dequeue (promote_ready)
                            v
   +-----------+     +--------------+      +---------------------+
   | Supervisor| --> |   Worker(s)  | ---> | CapabilityDispatcher|
   | assign    |     | STARTING..   |      | lookup/version/     |
   | heartbeat |     | READY/BUSY   |      | fallback/trace      |
   | escalate  |     | RETRYING     |      +----------+----------+
   | health    |     | FAILED/STOP  |                 | handler
   +-----+-----+     +------+-------+                  v
         |                  |                 +-----------------+
         | escalate         | run             | ExecutionEngine |
         v                  +---------------> | ctx/state/result|
   +-----------+                              | timeout/cancel  |
   | libs/alerts|                             +--------+--------+
   +-----------+                                       |
                                     metrics + audit   v
                          libs/metrics (collectors)  libs/audit (extra_events)
```

## Nguyên tắc tái dùng
- **Không fork**: `JobQueue`, `AuditTrail`, metrics collectors dùng nguyên; chỉ mở rộng
  additive (metric names mới, `AuditTrail(extra_events=...)`).
- **Không hardcode business logic**: dispatcher chỉ chạy handler được register từ ngoài.
- **Không network**: toàn bộ in-memory, stdlib; tích hợp adapter/alert giữ dry-run tới khi bật.
