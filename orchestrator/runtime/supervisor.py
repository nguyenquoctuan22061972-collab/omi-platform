"""Supervisor Runtime (PRD-013 E). Điều phối worker — hạ tầng runtime thuần, KHÔNG có
'CEO reasoning'.

Trách nhiệm:
  - assign jobs (cho worker dequeue mỗi tick; promote job hết backoff)
  - retry orchestration (dựa QueueOrchestrator backoff/DLQ)
  - worker heartbeat (theo dõi last-seen bằng clock inject)
  - failure escalation (tùy chọn qua libs/alerts, dry-run tới khi *_ALERT_ENABLED)
  - health aggregation (gộp trạng thái worker + hàng đợi)

Thuần stdlib, không network.
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

from .queue_orchestrator import QueueOrchestrator
from .worker import Worker, WorkerState


class Supervisor:
    def __init__(self, queue: QueueOrchestrator, workers: Optional[List[Worker]] = None,
                 alerts=None, heartbeat_timeout_s: float = 30.0,
                 clock: Optional[Callable[[], float]] = None):
        self.queue = queue
        self.workers: List[Worker] = list(workers or [])
        self.alerts = alerts                 # libs.alerts.AlertEngine hoặc None
        self.heartbeat_timeout_s = heartbeat_timeout_s
        self._clock = clock or time.monotonic
        self._seen: Dict[str, float] = {}
        self.escalations: List[Dict] = []
        for w in self.workers:
            self._seen[w.name] = self._clock()

    def add_worker(self, worker: Worker) -> None:
        self.workers.append(worker)
        self._seen[worker.name] = self._clock()

    # ---- assign / tick ----
    def tick(self) -> List[Dict]:
        """1 nhịp điều phối: promote backoff → mỗi worker xử lý 1 job → cập nhật heartbeat."""
        self.queue.promote_ready()
        results = []
        for w in self.workers:
            out = w.run_once()
            self._seen[w.name] = self._clock()      # ghi nhận heartbeat khi thấy worker hoạt động
            if out is not None:
                results.append({"worker": w.name, **out})
        return results

    def run(self, max_ticks: int = 1000) -> int:
        n = 0
        while n < max_ticks:
            self.tick()
            n += 1
            active = any(w.state not in (WorkerState.STOPPED, WorkerState.FAILED) for w in self.workers)
            if self.queue.depth() == 0 or not active:
                break
        return n

    # ---- heartbeat / escalation ----
    def heartbeats(self) -> List[Dict]:
        return [w.heartbeat() for w in self.workers]

    def stale_workers(self, now: Optional[float] = None) -> List[str]:
        t = now if now is not None else self._clock()
        return [name for name, seen in self._seen.items()
                if (t - seen) > self.heartbeat_timeout_s]

    def escalate_failures(self, now: Optional[float] = None) -> List[Dict]:
        """Escalate worker FAILED hoặc heartbeat quá hạn. Gửi qua alerts nếu có (dry-run mặc định)."""
        out = []
        stale = set(self.stale_workers(now))
        for w in self.workers:
            reason = None
            if w.state == WorkerState.FAILED:
                reason = "worker_failed"
            elif w.name in stale:
                reason = "heartbeat_stale"
            if reason:
                rec = {"worker": w.name, "reason": reason, "state": w.state.value}
                if self.alerts is not None:
                    try:
                        rec["alert"] = self.alerts.broadcast("critical",
                                                             f"[supervisor] {w.name}: {reason}")
                    except Exception:
                        rec["alert"] = "alert_error"
                self.escalations.append(rec)
                out.append(rec)
        return out

    # ---- health aggregation ----
    def health(self) -> Dict:
        counts: Dict[str, int] = {}
        for w in self.workers:
            counts[w.state.value] = counts.get(w.state.value, 0) + 1
        total = len(self.workers)
        healthy_workers = sum(1 for w in self.workers
                              if w.state in (WorkerState.READY, WorkerState.BUSY,
                                             WorkerState.RETRYING, WorkerState.STARTING))
        if total == 0:
            status = "down"
        elif healthy_workers == 0:
            status = "down"
        elif healthy_workers < total:
            status = "degraded"
        else:
            status = "healthy"
        return {"status": status, "workers": total, "healthy": healthy_workers,
                "by_state": counts, "queue_depth": self.queue.depth(),
                "retry_count": self.queue.retry_count}
