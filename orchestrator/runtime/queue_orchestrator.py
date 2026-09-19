"""Queue Orchestration (PRD-013 B). TÁI DÙNG hàng đợi sẵn có
apps/content-factory/queue/jobqueue.py (priority heap, dead-letter). KHÔNG fork.

Bổ sung lớp điều phối additive:
  - exponential backoff cho retry (giữ job ở 'delayed' tới khi đủ thời gian)
  - dead-letter khi hết lượt (dùng JobQueue.fail sẵn có)
  - metrics: queue depth (pending) + retry_count

Thuần stdlib, in-memory, không network.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Callable, Dict, List, Optional, Tuple

# Reuse hàng đợi hiện có (thư mục có dấu '-' nên nạp qua sys.path, giống test_queue.py).
_QDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "apps", "content-factory", "queue"))
if _QDIR not in sys.path:
    sys.path.insert(0, _QDIR)
from jobqueue import Job, JobQueue  # noqa: E402  (module tái dùng, không sửa)


class QueueOrchestrator:
    """Bọc JobQueue, thêm backoff + đo retry. clock inject được để test tất định."""

    def __init__(self, queue: Optional[JobQueue] = None, base_backoff_s: float = 1.0,
                 max_backoff_s: float = 300.0, clock: Optional[Callable[[], float]] = None,
                 metrics=None):
        self.q = queue or JobQueue()
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self._clock = clock or time.monotonic
        self.metrics = metrics
        self._delayed: List[Tuple[float, Job]] = []   # (ready_at, job)
        self._retry_count = 0

    # ---- enqueue / dequeue (passthrough, có promote backoff) ----
    def enqueue(self, kind: str, payload: Optional[Dict] = None, priority: int = 5,
                max_retries: int = 3) -> str:
        job = Job(kind=kind, payload=payload or {}, priority=priority, max_retries=max_retries)
        self._emit_metrics()
        return self.q.enqueue(job)

    def dequeue(self) -> Optional[Job]:
        self.promote_ready()          # đưa job đã hết backoff trở lại heap trước khi lấy
        job = self.q.dequeue()
        self._emit_metrics()
        return job

    # ---- kết quả job ----
    def complete(self, job: Job) -> None:
        self.q.complete(job)
        self._emit_metrics()

    def fail(self, job: Job, error: str = "") -> Dict:
        """Retry có exponential backoff nếu còn lượt; hết lượt → dead-letter (JobQueue.fail)."""
        if job.attempts < job.max_retries:
            delay = min(self.base_backoff_s * (2 ** (job.attempts - 1)), self.max_backoff_s)
            job._set("queued", f"retry backoff {delay}s sau lỗi: {error}")
            self._delayed.append((self._clock() + delay, job))
            self._retry_count += 1
            self._emit_metrics()
            return {"action": "retry", "attempt": job.attempts, "delay_s": delay}
        # Hết lượt → dùng cơ chế dead-letter sẵn có (attempts đã >= max_retries).
        outcome = self.q.fail(job, error)   # -> 'dead'
        self._emit_metrics()
        return {"action": outcome, "attempt": job.attempts, "delay_s": 0}

    def promote_ready(self, now: Optional[float] = None) -> int:
        """Đưa các job đã đủ thời gian backoff quay lại heap. Trả số job được promote."""
        t = now if now is not None else self._clock()
        ready = [(rt, j) for (rt, j) in self._delayed if rt <= t]
        self._delayed = [(rt, j) for (rt, j) in self._delayed if rt > t]
        for _, job in ready:
            self.q.enqueue(job)       # status đã 'queued' → dequeue sẽ nhận
        if ready:
            self._emit_metrics()
        return len(ready)

    # ---- metrics ----
    def depth(self) -> int:
        """Queue depth = job đang chờ trong heap + đang delayed backoff."""
        return self.q.stats()["pending"] + len(self._delayed)

    @property
    def retry_count(self) -> int:
        return self._retry_count

    def metrics_snapshot(self) -> Dict[str, float]:
        from libs.metrics.collectors import build_snapshot  # reuse Phase12 collectors
        return build_snapshot(queue_pending=self.depth(), retry_count=self._retry_count)

    def _emit_metrics(self) -> None:
        if not self.metrics:
            return
        try:
            self.metrics.set("queue_size", self.depth())
            self.metrics.set("retry_count", self._retry_count)
        except Exception:
            pass

    def stats(self) -> Dict:
        s = self.q.stats()
        s.update({"delayed": len(self._delayed), "retry_count": self._retry_count,
                  "depth": self.depth()})
        return s
