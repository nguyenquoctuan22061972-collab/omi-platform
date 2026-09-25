"""Zalo hardened runtime (PRD-016). Bọc zalo_pipeline với idempotency + retry + rate-limit
+ observability (metrics/logs/alerts). Reuse: zalo_pipeline, libs/metrics, libs/logging, libs/alerts.
Thuần stdlib, không network."""
from __future__ import annotations

import os
import sys
import time
from typing import Callable, Dict, List, Mapping, Optional

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "zalo-ai-company", "src"))
from zalo_pipeline import handle_inbound              # noqa: E402 (reuse E2E pipeline)
from libs.metrics import MockProvider                 # noqa: E402
from libs.logging.shipping import FileShipper         # noqa: E402
from libs.alerts.engine import AlertEngine            # noqa: E402


class RateLimiter:
    """Token bucket đơn giản (per-minute)."""
    def __init__(self, per_min: int = 60, clock: Optional[Callable[[], float]] = None):
        self.capacity = per_min
        self.tokens = float(per_min)
        self.rate = per_min / 60.0
        self._clock = clock or time.monotonic
        self._last = self._clock()

    def allow(self) -> bool:
        now = self._clock()
        self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.rate)
        self._last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class ZaloRuntime:
    def __init__(self, env: Optional[Mapping[str, str]] = None, rate_per_min: int = 60,
                 log_path: Optional[str] = None, clock: Optional[Callable[[], float]] = None):
        self.env = env or {}
        self.metrics = MockProvider()
        self.shipper = FileShipper(log_path) if log_path else None
        self.alerts = AlertEngine(env=self.env)
        self.limiter = RateLimiter(rate_per_min, clock=clock)
        self._seen: set = set()          # idempotency
        self._success = 0
        self._failure = 0
        self._retries = 0

    def _event_id(self, event: Dict) -> str:
        msg = event.get("message") or {}
        mid = msg.get("msg_id") if isinstance(msg, dict) else ""
        uid = (event.get("sender") or {}).get("id") or event.get("user_id") or ""
        return mid or f"{uid}:{(msg.get('text','') if isinstance(msg,dict) else '')}"

    def _log(self, rec: Dict) -> None:
        if self.shipper:
            try:
                self.shipper.ship(rec)
            except Exception:
                pass

    def process(self, event: Dict, max_tries: int = 3) -> Dict:
        eid = self._event_id(event)
        # idempotency
        if eid in self._seen:
            self._log({"level": "info", "event_id": eid, "status": "duplicate"})
            return {"status": "duplicate", "event_id": eid}
        # rate limit
        if not self.limiter.allow():
            self._log({"level": "warn", "event_id": eid, "status": "rate_limited"})
            return {"status": "rate_limited", "event_id": eid}
        # retry loop
        last = None
        for attempt in range(1, max_tries + 1):
            res = handle_inbound(event, env=self.env)
            if res.get("ok"):
                self._seen.add(eid)
                self._success += 1
                self.metrics.set("execution_success", self._success)
                self.metrics.set("retry_count", self._retries)
                self._log({"level": "info", "event_id": eid, "status": "ok", "attempt": attempt})
                return {"status": "ok", "event_id": eid, "attempt": attempt,
                        "ready_to_go_live": res.get("ready_to_go_live"), "reply": res.get("reply")}
            last = res
            self._retries += 1
        # all attempts failed
        self._failure += 1
        self.metrics.set("execution_failure", self._failure)
        self.metrics.set("retry_count", self._retries)
        self.alerts.broadcast("critical", f"[WF005] xử lý thất bại event {eid}")
        self._log({"level": "error", "event_id": eid, "status": "failed", "detail": last})
        return {"status": "failed", "event_id": eid, "detail": last}

    def snapshot(self) -> Dict:
        return {"success": self._success, "failure": self._failure, "retries": self._retries,
                "metrics": self.metrics.collect()}
