"""QA Runner (PRD-016). Chạy 4 Gate theo callable, ghi QAHistory; FAIL → RollbackLog + rollback cb.
Reuse QAHistory + RollbackLog. Thuần stdlib."""
from __future__ import annotations

import os
import sys
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from qa_history import QAHistory, GATES     # noqa: E402
from rollback_log import RollbackLog        # noqa: E402


class QARunner:
    def __init__(self, qa: Optional[QAHistory] = None, rollback: Optional[RollbackLog] = None):
        self.qa = qa or QAHistory()
        self.rollback = rollback or RollbackLog()

    def run_gates(self, target: str, gates: List[Tuple[str, str, Callable[[], bool]]],
                  on_rollback: Optional[Callable[[], None]] = None) -> Dict:
        """gates: [(gate_name, check_name, fn->bool)]. Trả tổng hợp; FAIL đầu tiên → rollback."""
        results = []
        for gate, name, fn in gates:
            try:
                ok = bool(fn())
            except Exception as e:
                ok = False
                name = f"{name} (exc:{type(e).__name__})"
            self.qa.record(gate, name, "PASS" if ok else "FAIL")
            results.append({"gate": gate, "name": name, "result": "PASS" if ok else "FAIL"})
            if not ok:
                self.rollback.record(target, f"gate FAIL: {gate}/{name}")
                if on_rollback:
                    try:
                        on_rollback()
                    except Exception:
                        pass
                return {"passed": False, "failed_gate": gate, "results": results}
        return {"passed": True, "results": results}
