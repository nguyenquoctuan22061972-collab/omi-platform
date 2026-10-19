"""Command Hub (AFFOS command path wiring).

Nối đường thực thi THẬT bằng module hiện có — KHÔNG tạo orchestrator thứ hai:

    Console → CommandHub.submit → DispatchEngine/QueueOrchestrator (enqueue)
            → Worker → ExecutionEngine (capability handler)
            → ResultStore (persist) → Console đọc lại theo correlation_id

- correlation_id/task_id xuyên suốt (reuse libs/logging.new_correlation_id).
- Tác vụ rủi ro thấp, thuần tính toán/validate; KHÔNG network, KHÔNG tiền, KHÔNG deploy.
- Idempotent: ResultStore khóa theo correlation_id.
- Trạng thái: QUEUED → RUNNING → SUCCEEDED | FAILED ; BLOCKED khi không route được.

Thuần stdlib.
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Dict, Optional

_HERE = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from orchestrator.runtime.dispatcher import CapabilityDispatcher
from orchestrator.runtime.queue_orchestrator import QueueOrchestrator
from orchestrator.runtime.dispatch_engine import DispatchEngine
from orchestrator.runtime.worker import Worker
from orchestrator.agents import Agent, AgentPool
from orchestrator.runtime import result_store as rs

try:
    from libs.logging.structured import new_correlation_id
except Exception:  # pragma: no cover - logging helper optional
    def new_correlation_id() -> str:
        return "cor_" + uuid.uuid4().hex[:16]

CAPABILITY = "console.command.execute"
ALLOWED_COMMANDS = {"build", "fix"}          # deploy KHÔNG thực thi ở đây (gated PR-002)
WORKER_ID = "builder-01"


def _new_task_id() -> str:
    return "AFFOS-EXEC-" + uuid.uuid4().hex[:12]


class CommandHub:
    def __init__(self, store: Optional[rs.ResultStore] = None, env: Optional[Dict] = None):
        self.store = store or rs.ResultStore(
            path=(env or {}).get("AFFOS_RESULT_DB", ":memory:"), env=env or {})
        self.dispatcher = CapabilityDispatcher()
        self.dispatcher.register(CAPABILITY, self._capability, version="1.0")
        self.queue = QueueOrchestrator()
        self.pool = AgentPool()
        self.pool.add(Agent(WORKER_ID, [CAPABILITY], self.dispatcher))
        self.engine_router = DispatchEngine(self.pool, strategy="least_busy", queue=self.queue)
        self.worker = Worker(WORKER_ID, self.queue, self.dispatcher)
        self.worker.start()

    # ---- the real, low-risk unit of work (runs inside ExecutionEngine) ----
    def _capability(self, ctx) -> Dict:
        p = ctx.payload
        cid = p.get("correlation_id")
        # mark RUNNING (persist, idempotent)
        self.store.put({"correlation_id": cid, "status": rs.RUNNING,
                        "worker": ctx.actor, "capability": ctx.capability})
        try:
            command = p.get("command")
            target = p.get("target")
            if not target:
                raise ValueError("target required")
            # deterministic, side-effect-free work (validation/preview plan) — no network/money
            output = {
                "command": command, "target": target, "validated": True,
                "steps": {"build": ["reuse module", "additive change", "4-gate QA"],
                          "fix": ["reproduce", "root-cause", "patch", "regression"]}.get(command, []),
                "note": "executed via orchestrator (dry-run safe; no external calls)",
            }
        except Exception as e:
            self.store.put({"correlation_id": cid, "status": rs.FAILED,
                            "error": f"{type(e).__name__}: {e}",
                            "worker": ctx.actor, "capability": ctx.capability})
            raise  # let ExecutionEngine record FAILED/metrics too
        self.store.put({"correlation_id": cid, "status": rs.SUCCEEDED, "result": output,
                        "worker": ctx.actor, "capability": ctx.capability})
        return output

    # ---- Console → Queue ----
    def submit(self, command: str, target: str, task_id: Optional[str] = None,
               correlation_id: Optional[str] = None, max_retries: int = 1) -> Dict:
        task_id = task_id or _new_task_id()
        correlation_id = correlation_id or new_correlation_id()
        base = {"correlation_id": correlation_id, "task_id": task_id,
                "command": command, "target": target}
        if command not in ALLOWED_COMMANDS or not self.pool.capable(CAPABILITY):
            rec = self.store.put({**base, "status": rs.BLOCKED,
                                  "error": f"command not executable here: {command}"})
            return {"ok": False, "status": rs.BLOCKED, "task_id": task_id,
                    "correlation_id": correlation_id, "reason": rec["error"]}
        self.store.put({**base, "status": rs.QUEUED})
        job_id = self.engine_router.submit_async(
            CAPABILITY, payload=base, max_retries=max_retries)
        return {"ok": True, "status": rs.QUEUED, "task_id": task_id,
                "correlation_id": correlation_id, "job_id": job_id}

    # ---- Queue → Worker (drive the real worker) ----
    def drain(self, max_iterations: int = 50) -> int:
        return self.worker.run_forever(max_iterations=max_iterations)

    # ---- Result Store → Console ----
    def result(self, correlation_id: str) -> Optional[Dict]:
        return self.store.get(correlation_id)

    # convenience: submit + drain in one call (synchronous execution through the real path)
    def run(self, command: str, target: str, **kw) -> Dict:
        sub = self.submit(command, target, **kw)
        if sub["status"] == rs.BLOCKED:
            return sub
        self.drain()
        rec = self.result(sub["correlation_id"]) or {}
        return {**sub, "status": rec.get("status", sub["status"]),
                "result": rec.get("result"), "error": rec.get("error", "")}
