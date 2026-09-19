"""Cost Guard (PRD-014 E). Theo dõi & chặn chi phí thực thi theo ngân sách.

- cost_table: capability -> chi phí mỗi lần (đơn vị trừu tượng: token/credit/VND...).
- charge(): trừ ngân sách nếu đủ; nếu vượt → chặn (không trừ), trả blocked.
- can_afford(), remaining(), reset(), snapshot().

KHÔNG gọi billing thật; thuần kế toán in-memory. Dùng bởi Agent/DispatchEngine trước khi chạy.
"""
from __future__ import annotations

from typing import Dict, Optional


class CostGuard:
    def __init__(self, budget: float, cost_table: Optional[Dict[str, float]] = None,
                 default_cost: float = 1.0, metrics=None):
        self.budget = float(budget)
        self.cost_table = dict(cost_table or {})
        self.default_cost = float(default_cost)
        self.metrics = metrics
        self.spent = 0.0
        self.blocked_count = 0
        self.by_capability: Dict[str, float] = {}

    def cost_of(self, capability: str, units: float = 1.0) -> float:
        return self.cost_table.get(capability, self.default_cost) * units

    def remaining(self) -> float:
        return self.budget - self.spent

    def can_afford(self, capability: str, units: float = 1.0) -> bool:
        return self.cost_of(capability, units) <= self.remaining() + 1e-9

    def charge(self, capability: str, units: float = 1.0) -> Dict:
        cost = self.cost_of(capability, units)
        if cost > self.remaining() + 1e-9:
            self.blocked_count += 1
            return {"ok": False, "blocked": True, "capability": capability,
                    "cost": cost, "remaining": self.remaining()}
        self.spent += cost
        self.by_capability[capability] = self.by_capability.get(capability, 0.0) + cost
        self._emit()
        return {"ok": True, "blocked": False, "capability": capability,
                "cost": cost, "remaining": self.remaining()}

    def reset(self) -> None:
        self.spent = 0.0
        self.blocked_count = 0
        self.by_capability = {}
        self._emit()

    def _emit(self) -> None:
        if not self.metrics:
            return
        try:  # metrics không được làm hỏng luồng chính
            self.metrics.set("cost_spent", self.spent)
        except Exception:
            pass

    def snapshot(self) -> Dict:
        return {"budget": self.budget, "spent": round(self.spent, 6),
                "remaining": round(self.remaining(), 6), "blocked": self.blocked_count,
                "by_capability": {k: round(v, 6) for k, v in self.by_capability.items()}}
