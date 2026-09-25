"""Skill Registry (PRD-016). Danh bạ skill (mục tiêu 400). Đăng ký + tra cứu theo category."""
from __future__ import annotations

import json
from typing import Dict, List, Optional


class SkillRegistry:
    def __init__(self, capacity: int = 400):
        self.capacity = capacity
        self._s: Dict[str, Dict] = {}

    def register(self, skill_id: str, name: str, category: str, handler_ref: str = "") -> Dict:
        if len(self._s) >= self.capacity and skill_id not in self._s:
            raise OverflowError("vượt capacity")
        spec = {"id": skill_id, "name": name, "category": category, "handler_ref": handler_ref}
        self._s[skill_id] = spec
        return spec

    def get(self, skill_id: str) -> Optional[Dict]:
        return self._s.get(skill_id)

    def by_category(self, category: str) -> List[str]:
        return [s["id"] for s in self._s.values() if s["category"] == category]

    def count(self) -> int:
        return len(self._s)

    def load_seed(self, path: str) -> int:
        data = json.load(open(path, encoding="utf-8"))
        for s in data.get("skills", []):
            self.register(s["id"], s["name"], s["category"], s.get("handler_ref", ""))
        return self.count()

    def stats(self) -> Dict:
        by_cat: Dict[str, int] = {}
        for s in self._s.values():
            by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1
        return {"registered": self.count(), "capacity": self.capacity, "by_category": by_cat}
