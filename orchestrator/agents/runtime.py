"""Agent Runtime (PRD-014 C). Agent nhẹ = 1 trong 800 AI Agent tương lai.

Mỗi Agent nắm 1 tập capability (tên) + chạy qua CapabilityDispatcher (PRD-013 C) và
ExecutionSandbox/Engine (PRD-014 B / PRD-013 A). Tuỳ chọn kiểm CostGuard (PRD-014 E)
trước khi chạy. KHÔNG có 'CEO reasoning' — chỉ thực thi.

Thuần stdlib, không network.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from orchestrator.runtime.dispatcher import CapabilityDispatcher, CapabilityNotFound
from orchestrator.runtime.execution import ExecutionContext, ExecutionEngine
from orchestrator.runtime.sandbox import ExecutionSandbox, SandboxResult


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class Agent:
    def __init__(self, agent_id: str, capabilities: List[str], dispatcher: CapabilityDispatcher,
                 sandbox: Optional[ExecutionSandbox] = None, cost_guard=None):
        self.id = agent_id
        self.capabilities = list(capabilities)
        self.dispatcher = dispatcher
        self.sandbox = sandbox or ExecutionSandbox(ExecutionEngine())
        self.cost_guard = cost_guard
        self.state = AgentState.IDLE
        self.runs = 0

    def can(self, capability: str) -> bool:
        return capability in self.capabilities and self.dispatcher.has(capability)

    def run(self, capability: str, payload: Optional[Dict] = None,
            version: Optional[str] = None, fallback: Optional[str] = None) -> Dict:
        if capability not in self.capabilities:
            self.state = AgentState.ERROR
            return {"agent": self.id, "ok": False, "reason": "capability_not_assigned"}
        # Cost guard (nếu có): chặn trước khi chạy.
        if self.cost_guard is not None and not self.cost_guard.can_afford(capability):
            self.state = AgentState.ERROR
            return {"agent": self.id, "ok": False, "reason": "budget_exceeded",
                    "remaining": self.cost_guard.remaining()}
        try:
            name, ver, handler = self.dispatcher.dispatch(capability, version=version, fallback=fallback)
        except CapabilityNotFound as e:
            self.state = AgentState.ERROR
            return {"agent": self.id, "ok": False, "reason": f"dispatch_failed: {e}"}

        self.state = AgentState.RUNNING
        ctx = ExecutionContext(capability=name, payload=payload or {}, actor=self.id)
        sres: SandboxResult = self.sandbox.run(ctx, handler)
        self.runs += 1
        if sres.ok and self.cost_guard is not None:
            self.cost_guard.charge(capability)   # chỉ trừ khi chạy thành công
        self.state = AgentState.DONE if sres.ok else AgentState.ERROR
        return {"agent": self.id, "ok": sres.ok, "capability": name, "version": ver,
                "sandbox": sres.to_dict()}

    def status(self) -> Dict:
        return {"id": self.id, "state": self.state.value, "runs": self.runs,
                "capabilities": self.capabilities}


class AgentPool:
    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}

    def add(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def all(self) -> List[Agent]:
        return list(self._agents.values())

    def capable(self, capability: str) -> List[Agent]:
        return [a for a in self._agents.values() if a.can(capability)]

    def stats(self) -> Dict:
        by_state: Dict[str, int] = {}
        for a in self._agents.values():
            by_state[a.state.value] = by_state.get(a.state.value, 0) + 1
        return {"agents": len(self._agents), "by_state": by_state}
