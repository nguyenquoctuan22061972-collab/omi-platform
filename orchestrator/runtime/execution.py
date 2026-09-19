"""Execution Engine (PRD-013 A). Vòng đời chạy một đơn vị công việc:

  PENDING -> RUNNING -> {SUCCEEDED | FAILED | CANCELLED | TIMED_OUT}

Tái dùng libs/metrics (execution_success/failure, workflow_duration_ms) và libs/audit
(qua extra_events, không đổi EVENTS gốc). KHÔNG tạo workflow engine mới — chỉ chạy 1 callable
được inject (capability handler). Thuần stdlib, không network.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

# Sự kiện audit riêng của orchestrator (đưa qua AuditTrail(extra_events=...) — không đụng EVENTS gốc).
AUDIT_EVENTS = {
    "execution_start",
    "execution_success",
    "execution_failure",
    "execution_cancelled",
    "execution_timeout",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

    def is_terminal(self) -> bool:
        return self in (ExecutionState.SUCCEEDED, ExecutionState.FAILED,
                        ExecutionState.CANCELLED, ExecutionState.TIMED_OUT)


class CancelToken:
    """Cờ hủy hợp tác (cooperative). Handler có thể đọc .cancelled để dừng sớm."""
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


class ExecutionContext:
    """Ngữ cảnh 1 lần chạy: capability + payload + timeout + cancel token."""
    def __init__(self, capability: str, payload: Optional[Dict] = None,
                 timeout_s: Optional[float] = None, actor: str = "orchestrator",
                 exec_id: Optional[str] = None):
        self.id = exec_id or ("exec_" + uuid.uuid4().hex[:16])
        self.capability = capability
        self.payload = payload or {}
        self.timeout_s = timeout_s
        self.actor = actor
        self.created_at = _now()
        self.cancel_token = CancelToken()

    def cancel(self) -> None:
        self.cancel_token.cancel()

    def to_dict(self) -> Dict:
        return {"id": self.id, "capability": self.capability, "timeout_s": self.timeout_s,
                "actor": self.actor, "created_at": self.created_at}


class ExecutionResult:
    def __init__(self, context: ExecutionContext, state: ExecutionState,
                 output: Any = None, error: str = "", duration_ms: float = 0.0,
                 attempts: int = 1):
        self.id = context.id
        self.capability = context.capability
        self.state = state
        self.output = output
        self.error = error
        self.duration_ms = duration_ms
        self.attempts = attempts

    @property
    def ok(self) -> bool:
        return self.state == ExecutionState.SUCCEEDED

    def to_dict(self) -> Dict:
        return {"id": self.id, "capability": self.capability, "state": self.state.value,
                "error": self.error, "duration_ms": round(self.duration_ms, 3),
                "attempts": self.attempts}


class ExecutionEngine:
    """Chạy 1 callable trong vòng đời có kiểm soát timeout + cancellation.

    metrics: object có .set(name, value) (vd libs.metrics MockProvider) hoặc None.
    audit:   libs.audit.AuditTrail (nên khởi tạo với extra_events=AUDIT_EVENTS) hoặc None.
    """
    def __init__(self, metrics=None, audit=None):
        self.metrics = metrics
        self.audit = audit
        self._success = 0
        self._failure = 0

    def _emit_metrics(self, duration_ms: float) -> None:
        if not self.metrics:
            return
        try:
            self.metrics.set("execution_success", self._success)
            self.metrics.set("execution_failure", self._failure)
            self.metrics.set("workflow_duration_ms", duration_ms)
        except Exception:
            pass  # metrics không bao giờ được làm hỏng execution

    def _audit(self, event: str, ctx: ExecutionContext, meta: Optional[Dict] = None) -> None:
        if not self.audit:
            return
        try:
            self.audit.record(event, actor=ctx.actor, target=ctx.capability, meta=meta or {})
        except Exception:
            pass

    def run(self, context: ExecutionContext, handler: Callable[[ExecutionContext], Any],
            attempts: int = 1) -> ExecutionResult:
        """Thực thi handler(context) với timeout & cancellation. Không ném — luôn trả ExecutionResult."""
        self._audit("execution_start", context, {"exec_id": context.id})

        # Hủy trước khi chạy.
        if context.cancel_token.cancelled:
            res = ExecutionResult(context, ExecutionState.CANCELLED, error="cancelled trước khi chạy",
                                  attempts=attempts)
            self._audit("execution_cancelled", context, {"exec_id": context.id})
            return res

        box: Dict[str, Any] = {}
        def _target() -> None:
            try:
                box["output"] = handler(context)
            except Exception as e:  # lỗi handler → FAILED
                box["error"] = f"{type(e).__name__}: {e}"

        t0 = time.monotonic()
        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        worker.join(context.timeout_s)
        duration_ms = (time.monotonic() - t0) * 1000.0

        if worker.is_alive():
            # Quá thời gian: báo hủy hợp tác + đánh dấu TIMED_OUT (thread daemon sẽ tự tiêu khi tiến trình dừng).
            context.cancel_token.cancel()
            self._failure += 1
            self._emit_metrics(duration_ms)
            res = ExecutionResult(context, ExecutionState.TIMED_OUT,
                                  error=f"timeout sau {context.timeout_s}s", duration_ms=duration_ms,
                                  attempts=attempts)
            self._audit("execution_timeout", context, {"exec_id": context.id, "timeout_s": context.timeout_s})
            return res

        if "error" in box:
            self._failure += 1
            self._emit_metrics(duration_ms)
            res = ExecutionResult(context, ExecutionState.FAILED, error=box["error"],
                                  duration_ms=duration_ms, attempts=attempts)
            self._audit("execution_failure", context, {"exec_id": context.id, "error": box["error"]})
            return res

        if context.cancel_token.cancelled:
            res = ExecutionResult(context, ExecutionState.CANCELLED, duration_ms=duration_ms,
                                  attempts=attempts)
            self._audit("execution_cancelled", context, {"exec_id": context.id})
            return res

        self._success += 1
        self._emit_metrics(duration_ms)
        res = ExecutionResult(context, ExecutionState.SUCCEEDED, output=box.get("output"),
                              duration_ms=duration_ms, attempts=attempts)
        self._audit("execution_success", context, {"exec_id": context.id})
        return res

    @property
    def counters(self) -> Dict[str, int]:
        return {"success": self._success, "failure": self._failure}
