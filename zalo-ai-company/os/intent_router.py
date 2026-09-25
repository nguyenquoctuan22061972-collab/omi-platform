"""Intent Router (PRD-016). Định tuyến text/intent → (department, agent, skill).
Rule-based keyword + fallback; reuse AgentRegistry/SkillRegistry. Không network."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# intent -> (department, keyword list, skill_category)
INTENT_RULES: List[Tuple[str, str, List[str], str]] = [
    ("sales_inquiry", "sales", ["giá", "báo giá", "mua", "premium", "gói"], "sales"),
    ("support", "crm", ["lỗi", "hỗ trợ", "help", "sự cố"], "support"),
    ("content", "content", ["viết", "bài", "content", "đăng"], "content"),
    ("call_intelligence", "engineering", ["ghi âm", "cuộc gọi", "call", "transcript"], "ai"),
    ("zalo_message", "zalo", ["zalo", "oa", "nhắn tin"], "messaging"),
]


class IntentRouter:
    def __init__(self, agents=None, skills=None):
        self.agents = agents
        self.skills = skills

    def classify(self, text: str) -> Dict:
        t = (text or "").lower()
        for intent, dept, kws, cat in INTENT_RULES:
            if any(k in t for k in kws):
                return {"intent": intent, "department": dept, "skill_category": cat, "matched": True}
        return {"intent": "general", "department": "crm", "skill_category": "support", "matched": False}

    def route(self, text: str) -> Dict:
        c = self.classify(text)
        agent_id = None
        skill_id = None
        if self.agents is not None:
            cands = self.agents.by_department(c["department"])
            agent_id = cands[0] if cands else None
        if self.skills is not None:
            cands = self.skills.by_category(c["skill_category"])
            skill_id = cands[0] if cands else None
        return {**c, "agent_id": agent_id, "skill_id": skill_id,
                "confidence": 0.9 if c["matched"] else 0.3}
