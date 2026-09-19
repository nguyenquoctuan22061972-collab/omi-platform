"""Metrics collectors (PRD-012 A). Additive — không sửa registry.py.

Gom số liệu từ runtime-health/queue/adapters/workflow (inject) → MockProvider chuẩn.
Không gọi hệ thống metrics thật.
"""
from __future__ import annotations

from typing import Dict

from .registry import MetricsRegistry, MockProvider, render_prometheus


def build_snapshot(
    health_ready: bool = False,
    queue_pending: int = 0,
    adapters_enabled: int = 0,
    workflow_count: int = 0,
    dashboard_latency_ms: float = 0.0,
    workflow_duration_ms: float = 0.0,
    adapter_latency_ms: float = 0.0,
    execution_success: int = 0,
    execution_failure: int = 0,
    retry_count: int = 0,
) -> Dict[str, float]:
    """Tạo snapshot metric chuẩn (registry.METRIC_NAMES) từ nguồn inject.

    Phase 12 Module A (additive): thêm workflow_duration_ms, adapter_latency_ms,
    execution_success/failure. Metric không truyền vẫn mặc định 0.0.
    """
    p = MockProvider({
        "workflow_count": workflow_count,
        "queue_size": queue_pending,
        "adapter_status": adapters_enabled,
        "dashboard_latency_ms": dashboard_latency_ms,
        "health_summary": 1.0 if health_ready else 0.0,
        "workflow_duration_ms": workflow_duration_ms,
        "adapter_latency_ms": adapter_latency_ms,
        "execution_success": execution_success,
        "execution_failure": execution_failure,
        "retry_count": retry_count,
    })
    return MetricsRegistry(p).snapshot()


def metrics_text(snapshot: Dict[str, float] | None = None, **sources) -> str:
    """Render Prometheus exposition text (không push tới Prometheus)."""
    snap = snapshot if snapshot is not None else build_snapshot(**sources)
    return render_prometheus(snap)
