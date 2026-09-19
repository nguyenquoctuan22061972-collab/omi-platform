"""Runtime Dashboard Data (PRD-014 F). Gom trạng thái runtime thành 1 dict JSON-serializable
cho dashboard — CHỈ DỮ LIỆU, không UI, không network.

Tái dùng:
  - supervisor.health() (PRD-013 E)
  - QueueOrchestrator.stats() (PRD-013 B)
  - CostGuard.snapshot() (PRD-014 E)
  - CapabilityRegistryV2.stats() (PRD-014 A)
  - AgentPool.stats() (PRD-014 C)
  - libs/metrics collectors.build_snapshot (Phase 12/13/14)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional


def build_dashboard(supervisor=None, queue=None, cost_guard=None, registry=None,
                    pool=None) -> Dict:
    """Trả snapshot tổng hợp. Mọi tham số optional — chỉ gom cái nào được truyền."""
    from libs.metrics.collectors import build_snapshot   # reuse collectors

    data: Dict = {"ts": datetime.now(timezone.utc).isoformat(), "sections": {}}
    s = data["sections"]

    queue_depth = 0
    retry_count = 0
    if queue is not None:
        qs = queue.stats()
        s["queue"] = qs
        queue_depth = qs.get("depth", qs.get("pending", 0))
        retry_count = qs.get("retry_count", 0)

    cost_spent = 0.0
    if cost_guard is not None:
        cs = cost_guard.snapshot()
        s["cost"] = cs
        cost_spent = cs.get("spent", 0.0)

    if supervisor is not None:
        s["health"] = supervisor.health()

    if registry is not None:
        s["capabilities"] = registry.stats()

    if pool is not None:
        s["agents"] = pool.stats()

    # Metric snapshot chuẩn (reuse collectors) — nguồn duy nhất cho số liệu.
    health_ready = bool(s.get("health", {}).get("status") == "healthy")
    s["metrics"] = build_snapshot(
        health_ready=health_ready,
        queue_pending=queue_depth,
        retry_count=retry_count,
        cost_spent=cost_spent,
    )
    return data
