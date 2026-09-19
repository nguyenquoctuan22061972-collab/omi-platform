"""Worker Runtime (PRD-013 D). Worker tái sử dụng lấy job từ QueueOrchestrator, phân giải
capability qua CapabilityDispatcher, chạy bằng ExecutionEngine.

Vòng đời: STARTING -> READY -> BUSY -> (RETRYING) -> ... -> STOPPED ; lỗi nội bộ -> FAILED.
Hỗ trợ graceful shutdown (dừng sau khi xong job đang chạy). Phát metrics + audit qua engine.
Thuần stdlib, không network.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from .dispatcher import CapabilityDispatcher, CapabilityNotFound
from .execution import ExecutionContext, ExecutionEngine, ExecutionState
from .queue_orchestrator import QueueOrchestrator


class WorkerState(str, Enum):
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    RETRYING = "retrying"
    FAILED = "failed"
    STOPPED = "stopped"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Worker:
    def __init__(self, name: str, queue: QueueOrchestrator, dispatcher: CapabilityDispatcher,
                 engine: Optional[ExecutionEngine] = None, default_timeout_s: Optional[float] = None):
        self.name = name
        self.queue = queue
        self.dispatcher = dispatcher
        self.engine = engine or ExecutionEngine()
        self.default_timeout_s = default_timeout_s
        self.state = WorkerState.STARTING
        self._stopping = False
        self.last_heartbeat = _now()
        self.processed = 0

    # ---- lifecycle ----
    def start(self) -> None:
        self.state = WorkerState.READY
        self._beat()

    def stop(self) -> None:
        """Graceful: đánh dấu dừng; job đang chạy vẫn hoàn tất."""
        self._stopping = True

    def _beat(self) -> None:
        self.last_heartbeat = _now()

    def heartbeat(self) -> Dict:
        return {"worker": self.name, "state": self.state.value,
                "last_heartbeat": self.last_heartbeat, "processed": self.processed}

    # ---- xử lý 1 job ----
    def run_once(self) -> Optional[Dict]:
        self._beat()
        if self._stopping:
            self.state = WorkerState.STOPPED
            return None
        if self.state == WorkerState.STARTING:
            self.start()

        job = self.queue.dequeue()
        if job is None:
            self.state = WorkerState.READY
            return None

        self.state = WorkerState.BUSY
        self._beat()
        # job.kind = tên capability; payload → context.
        try:
            _, _, handler = self.dispatcher.dispatch(job.kind, version=job.payload.get("_version"),
                                                     fallback=job.payload.get("_fallback"))
        except CapabilityNotFound as e:
            outcome = self.queue.fail(job, f"capability lỗi: {e}")
            self.state = WorkerState.RETRYING if outcome["action"] == "retry" else WorkerState.READY
            return {"job": job.id, "result": "dispatch_failed", "outcome": outcome}

        ctx = ExecutionContext(capability=job.kind, payload=job.payload,
                               timeout_s=self.default_timeout_s, actor=self.name)
        result = self.engine.run(ctx, handler, attempts=job.attempts)

        if result.state == ExecutionState.SUCCEEDED:
            self.queue.complete(job)
            self.processed += 1
            self.state = WorkerState.READY
            return {"job": job.id, "result": "succeeded", "duration_ms": result.duration_ms}

        outcome = self.queue.fail(job, result.error)
        self.state = WorkerState.RETRYING if outcome["action"] == "retry" else WorkerState.READY
        self._beat()
        return {"job": job.id, "result": result.state.value, "error": result.error, "outcome": outcome}

    def run_forever(self, max_iterations: int = 1000, sleep_s: float = 0.0) -> int:
        """Chạy tới khi hết job hoặc bị stop. Trả số vòng đã xử lý (test dùng max_iterations)."""
        n = 0
        while n < max_iterations and not self._stopping:
            out = self.run_once()
            n += 1
            if out is None and self.queue.depth() == 0:
                break
            if sleep_s:
                time.sleep(sleep_s)
        if self._stopping:
            self.state = WorkerState.STOPPED
        return n
