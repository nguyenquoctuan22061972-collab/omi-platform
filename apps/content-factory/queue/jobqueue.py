"""AI Job Queue (PRD-009 A): priority, retry, dead-letter, history, status timeline.

Thuần trong bộ nhớ, KHÔNG gọi API thật. Dùng cho điều phối job content-factory.
"""
from __future__ import annotations

import heapq
import itertools
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

STATUSES = ("queued", "running", "succeeded", "failed", "dead")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Job:
    def __init__(self, kind: str, payload: Dict, priority: int = 5, max_retries: int = 3):
        self.id = "job_" + uuid.uuid4().hex[:16]
        self.kind = kind
        self.payload = payload
        self.priority = priority          # nhỏ hơn = ưu tiên cao hơn
        self.max_retries = max_retries
        self.attempts = 0
        self.status = "queued"
        self.timeline: List[Dict] = [{"ts": _now(), "status": "queued"}]

    def _set(self, status: str, note: str = "") -> None:
        self.status = status
        self.timeline.append({"ts": _now(), "status": status, "note": note})

    def to_dict(self) -> Dict:
        return {"id": self.id, "kind": self.kind, "priority": self.priority,
                "attempts": self.attempts, "status": self.status, "timeline": self.timeline}


class JobQueue:
    def __init__(self):
        self._heap: List = []
        self._counter = itertools.count()
        self.jobs: Dict[str, Job] = {}
        self.dead_letter: List[Job] = []
        self.history: List[Dict] = []

    def enqueue(self, job: Job) -> str:
        self.jobs[job.id] = job
        heapq.heappush(self._heap, (job.priority, next(self._counter), job.id))
        return job.id

    def dequeue(self) -> Optional[Job]:
        while self._heap:
            _, _, jid = heapq.heappop(self._heap)
            job = self.jobs.get(jid)
            if job and job.status == "queued":
                job.attempts += 1
                job._set("running")
                return job
        return None

    def complete(self, job: Job) -> None:
        job._set("succeeded")
        self.history.append({"id": job.id, "result": "succeeded", "ts": _now()})

    def fail(self, job: Job, error: str = "") -> str:
        """Retry nếu còn lượt; hết → dead-letter."""
        if job.attempts < job.max_retries:
            job._set("queued", f"retry sau lỗi: {error}")
            heapq.heappush(self._heap, (job.priority, next(self._counter), job.id))
            return "requeued"
        job._set("dead", f"dead-letter: {error}")
        self.dead_letter.append(job)
        self.history.append({"id": job.id, "result": "dead", "ts": _now()})
        return "dead"

    def stats(self) -> Dict:
        by = {s: 0 for s in STATUSES}
        for j in self.jobs.values():
            by[j.status] = by.get(j.status, 0) + 1
        return {"total": len(self.jobs), "by_status": by,
                "dead_letter": len(self.dead_letter), "pending": len(self._heap)}
