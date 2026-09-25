"""QA History (PRD-016). Ghi kết quả QA theo 4 Gate; redact secret. Store JSON hoặc memory."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

GATES = {"architecture", "regression", "security", "production_safety"}
_SECRET_HINTS = ("token", "secret", "password", "api_key", "access_token", "key")


def _redact(meta: Dict) -> Dict:
    out = {}
    for k, v in (meta or {}).items():
        out[k] = "***redacted***" if any(h in k.lower() for h in _SECRET_HINTS) else v
    return out


class QAHistory:
    def __init__(self, store_path: Optional[str] = None):
        self.store_path = store_path
        self.records: List[Dict] = []
        if store_path and os.path.isfile(store_path):
            self.records = json.load(open(store_path, encoding="utf-8"))

    def record(self, gate: str, name: str, result: str, meta: Optional[Dict] = None) -> Dict:
        if gate not in GATES:
            raise ValueError(f"gate lạ: {gate}")
        if result not in ("PASS", "FAIL"):
            raise ValueError("result phải PASS/FAIL")
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "gate": gate,
               "name": name, "result": result, "meta": _redact(meta or {})}
        self.records.append(rec)
        if self.store_path:
            json.dump(self.records, open(self.store_path, "w", encoding="utf-8"), ensure_ascii=False)
        return rec

    def query(self, result: Optional[str] = None, gate: Optional[str] = None) -> List[Dict]:
        return [r for r in self.records
                if (result is None or r["result"] == result)
                and (gate is None or r["gate"] == gate)]

    def summary(self) -> Dict:
        return {"total": len(self.records),
                "pass": len(self.query("PASS")), "fail": len(self.query("FAIL")),
                "by_gate": {g: len(self.query(gate=g)) for g in GATES}}
