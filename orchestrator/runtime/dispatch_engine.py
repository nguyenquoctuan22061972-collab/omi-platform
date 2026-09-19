"""Dispatch Engine (PRD-014 D). Định tuyến task tới Agent phù hợp trong AgentPool.

Chiến lược:
  - round_robin: xoay vòng đều giữa các agent có capability.
  - least_busy : chọn agent có ít lần chạy nhất (self.runs).

Tuỳ chọn nối QueueOrchestrator (PRD-013 B) để submit bất đồng bộ (enqueue) thay vì chạy ngay.
Tái dùng AgentPool (PRD-014 C) — không fork. Thuần stdlib, không network.
"""
from __future__ import annotations

from typing import Dict, Optional

from orchestrator.agents.runtime import Agent, AgentPool


class NoCapableAgent(LookupError):
    pass


class DispatchEngine:
    def __init__(self, pool: AgentPool, strategy: str = "round_robin", queue=None):
        if strategy not in ("round_robin", "least_busy"):
            raise ValueError(f"strategy không hợp lệ: {strategy}")
        self.pool = pool
        self.strategy = strategy
        self.queue = queue
        self._rr: Dict[str, int] = {}   # con trỏ round-robin theo capability

    def route(self, capability: str) -> Agent:
        agents = self.pool.capable(capability)
        if not agents:
            raise NoCapableAgent(f"không agent nào phục vụ: {capability}")
        if self.strategy == "least_busy":
            return min(agents, key=lambda a: a.runs)
        # round_robin (ổn định theo id)
        agents = sorted(agents, key=lambda a: a.id)
        i = self._rr.get(capability, 0) % len(agents)
        self._rr[capability] = i + 1
        return agents[i]

    def submit(self, capability: str, payload: Optional[Dict] = None,
               version: Optional[str] = None) -> Dict:
        """Chạy ngay qua agent được route. Trả kết quả agent.run()."""
        agent = self.route(capability)
        return agent.run(capability, payload=payload, version=version)

    def submit_async(self, capability: str, payload: Optional[Dict] = None,
                     priority: int = 5, max_retries: int = 3) -> str:
        """Đưa task vào QueueOrchestrator (nếu có) để worker xử lý sau. Trả job_id."""
        if self.queue is None:
            raise RuntimeError("DispatchEngine chưa gắn queue để submit_async")
        return self.queue.enqueue(capability, payload=payload or {}, priority=priority,
                                  max_retries=max_retries)
