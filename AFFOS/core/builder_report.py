"""AFFOS Builder Report (PRD-017). Sinh báo cáo theo template chuẩn. Pure."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

SECTIONS = ["COMPLETED", "IN PROGRESS", "BLOCKED", "REAL DATA", "REAL REVENUE",
            "COST", "ERRORS", "SECURITY", "ARCHITECTURE CONFLICT",
            "DECISIONS REQUIRED FROM CTO", "NEXT 24H"]


def render(data: Optional[Dict] = None, date: str = "") -> str:
    data = data or {}
    d = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = ["AFFOS BUILDER REPORT", "", f"DATE: {d}", ""]
    for s in SECTIONS:
        lines.append(f"{s}:")
        items = data.get(s, [])
        if isinstance(items, str):
            items = [items]
        if items:
            lines += [f"- {x}" for x in items]
        else:
            lines.append("- —")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
