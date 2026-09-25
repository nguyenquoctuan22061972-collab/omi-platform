"""Agent Registry (PRD-016). Danh bạ agent (mục tiêu quy mô 800). Đăng ký + tra cứu.
Không tạo agent runtime mới — bổ trợ orchestrator/agents (reuse khi thực thi)."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

TIERS = {"orchestrator", "supervisor", "worker"}


class AgentRegistry:
    def __init__(self, capacity: int = 800):
        self.capacity = capacity
        self._a: Dict[str, Dict] = {}

    def register(self, agent_id: str, capabilities: List[str], department: str,
                 tier: str = "worker") -> Dict:
        if tier not in TIERS:
            raise ValueError(f"tier lạ: {tier}")
        if len(self._a) >= self.capacity and agent_id not in self._a:
            raise OverflowError("vượt capacity")
        spec = {"id": agent_id, "capabilities": list(capabilities),
                "department": department, "tier": tier}
        self._a[agent_id] = spec
        return spec

    def get(self, agent_id: str) -> Optional[Dict]:
        return self._a.get(agent_id)

    def by_capability(self, cap: str) -> List[str]:
        return [a["id"] for a in self._a.values() if cap in a["capabilities"]]

    def by_department(self, dep: str) -> List[str]:
        return [a["id"] for a in self._a.values() if a["department"] == dep]

    def count(self) -> int:
        return len(self._a)

    def load_seed(self, path: str) -> int:
        data = json.load(open(path, encoding="utf-8"))
        for a in data.get("agents", []):
            self.register(a["id"], a["capabilities"], a["department"], a.get("tier", "worker"))
        return self.count()

    def stats(self) -> Dict:
        by_dep: Dict[str, int] = {}
        for a in self._a.values():
            by_dep[a["department"]] = by_dep.get(a["department"], 0) + 1
        return {"registered": self.count(), "capacity": self.capacity, "by_department": by_dep}
