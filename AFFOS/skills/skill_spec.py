"""AFFOS Skill spec (PRD-017). Schema validate."""
from __future__ import annotations

from typing import Dict, List

FIELDS = ["id", "name", "version", "description", "required_tools",
          "input_schema", "output_schema", "cost", "permission", "status"]


def validate_skill(spec: Dict) -> List[str]:
    errs = [f"thiếu field: {f}" for f in FIELDS if f not in spec]
    if not isinstance(spec.get("required_tools"), list):
        errs.append("required_tools phải list")
    if not isinstance(spec.get("cost"), (int, float)):
        errs.append("cost phải số")
    return errs
