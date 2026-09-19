"""Execution Sandbox (PRD-014 B). Lớp bọc an toàn quanh ExecutionEngine (PRD-013 A):

  - allowlist capability (chặn capability ngoài danh sách)
  - giới hạn kích thước output (chống ngốn bộ nhớ)
  - timeout (uỷ quyền cho engine)
  - dry-run (không chạy handler, trả kết quả tổng hợp)

KHÔNG phải hộp cách ly OS-level (thuần stdlib) — là hàng rào runtime hợp tác. Không network.
Tái dùng ExecutionEngine/Context/State — không fork.
"""
from __future__ import annotations

from typing import Callable, Optional, Set

from .execution import ExecutionContext, ExecutionEngine, ExecutionResult, ExecutionState


class SandboxPolicy:
    def __init__(self, timeout_s: Optional[float] = 30.0, max_output_bytes: int = 1_000_000,
                 allow: Optional[Set[str]] = None, dry_run: bool = False):
        self.timeout_s = timeout_s
        self.max_output_bytes = max_output_bytes
        self.allow = set(allow) if allow is not None else None   # None = cho phép tất cả
        self.dry_run = dry_run

    def allowed(self, capability: str) -> bool:
        return self.allow is None or capability in self.allow


class SandboxResult:
    def __init__(self, result: Optional[ExecutionResult], blocked: bool = False,
                 violation: str = ""):
        self.result = result
        self.blocked = blocked
        self.violation = violation

    @property
    def ok(self) -> bool:
        return (not self.blocked) and self.result is not None and self.result.ok

    def to_dict(self):
        return {"blocked": self.blocked, "violation": self.violation,
                "result": self.result.to_dict() if self.result else None}


class ExecutionSandbox:
    def __init__(self, engine: Optional[ExecutionEngine] = None,
                 policy: Optional[SandboxPolicy] = None):
        self.engine = engine or ExecutionEngine()
        self.policy = policy or SandboxPolicy()

    def run(self, context: ExecutionContext, handler: Callable, attempts: int = 1) -> SandboxResult:
        # 1. allowlist
        if not self.policy.allowed(context.capability):
            return SandboxResult(None, blocked=True,
                                 violation=f"capability ngoài allowlist: {context.capability}")
        # 2. dry-run
        if self.policy.dry_run:
            res = ExecutionResult(context, ExecutionState.SUCCEEDED, output="<dry-run>",
                                  duration_ms=0.0, attempts=attempts)
            return SandboxResult(res)
        # 3. áp timeout policy nếu context chưa đặt
        if context.timeout_s is None:
            context.timeout_s = self.policy.timeout_s

        # 4. bọc handler để giới hạn output
        max_b = self.policy.max_output_bytes
        def _guarded(ctx):
            out = handler(ctx)
            try:
                size = len(out) if isinstance(out, (str, bytes, bytearray)) else len(repr(out))
            except Exception:
                size = 0
            if size > max_b:
                raise ValueError(f"output vượt giới hạn sandbox ({size} > {max_b} bytes)")
            return out

        res = self.engine.run(context, _guarded, attempts=attempts)
        return SandboxResult(res)
