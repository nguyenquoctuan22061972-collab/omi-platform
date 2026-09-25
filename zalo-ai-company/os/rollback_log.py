"""Rollback Log (PRD-016). Ghi sự kiện rollback (append-only). Store JSON hoặc memory."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional


class RollbackLog:
    def __init__(self, store_path: Optional[str] = None):
        self.store_path = store_path
        self.events: List[Dict] = []
        if store_path and os.path.isfile(store_path):
            self.events = json.load(open(store_path, encoding="utf-8"))

    def record(self, target: str, reason: str, from_ver: str = "", to_ver: str = "",
               actor: str = "builder") -> Dict:
        ev = {"ts": datetime.now(timezone.utc).isoformat(), "target": target,
              "reason": reason, "from": from_ver, "to": to_ver, "actor": actor}
        self.events.append(ev)
        if self.store_path:
            json.dump(self.events, open(self.store_path, "w", encoding="utf-8"), ensure_ascii=False)
        return ev

    def list(self) -> List[Dict]:
        return list(self.events)

    def last(self) -> Optional[Dict]:
        return self.events[-1] if self.events else None
