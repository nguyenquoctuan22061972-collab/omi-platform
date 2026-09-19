"""Metrics registry + provider abstraction (PRD-008 D). Mock provider; không network."""
from __future__ import annotations

from typing import Dict, Protocol

# Chỉ số expose.
METRIC_NAMES = [
    "workflow_count",
    "queue_size",
    "adapter_status",     # số adapter đang enabled+configured
    "dashboard_latency_ms",
    "health_summary",     # 1 = healthy, 0 = degraded
    # PRD-012 A (additive) — bổ sung theo yêu cầu Phase 12 Module A:
    "workflow_duration_ms",   # thời lượng chạy workflow gần nhất
    "adapter_latency_ms",     # độ trễ adapter gần nhất
    "execution_success",      # tổng lần chạy thành công
    "execution_failure",      # tổng lần chạy thất bại
    # PRD-013 B (additive) — queue orchestration:
    "retry_count",            # tổng lần retry trong hàng đợi
    # PRD-014 E (additive) — cost guard:
    "cost_spent",             # tổng chi phí đã tiêu (đơn vị trừu tượng)
]


class Provider(Protocol):
    def collect(self) -> Dict[str, float]: ...


class MockProvider:
    """Provider mock — trả số liệu tĩnh/được set. Thay bằng provider thật sau (giữ interface)."""

    def __init__(self, values: Dict[str, float] | None = None):
        self._values = {name: 0.0 for name in METRIC_NAMES}
        if values:
            self._values.update({k: v for k, v in values.items() if k in METRIC_NAMES})

    def set(self, name: str, value: float) -> None:
        if name not in METRIC_NAMES:
            raise KeyError(f"metric không hợp lệ: {name}")
        self._values[name] = float(value)

    def collect(self) -> Dict[str, float]:
        return dict(self._values)


class MetricsRegistry:
    def __init__(self, provider: Provider | None = None):
        self.provider = provider or MockProvider()

    def snapshot(self) -> Dict[str, float]:
        return self.provider.collect()


def render_prometheus(snapshot: Dict[str, float]) -> str:
    """Render text kiểu Prometheus exposition (chuỗi thuần — KHÔNG push tới Prometheus)."""
    lines = []
    for name, val in snapshot.items():
        lines.append(f"# TYPE omi_{name} gauge")
        lines.append(f"omi_{name} {val}")
    return "\n".join(lines) + "\n"
