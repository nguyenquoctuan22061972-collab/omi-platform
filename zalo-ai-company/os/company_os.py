"""Company OS façade (PRD-016). Kết dính 6 thành phần thành 1 runtime:
Agent Registry + Skill Registry + Intent Router + QA History + Rollback Log + (Vault RAG optional).

Không tạo trùng — chỉ compose module đã có. Thuần stdlib, không network.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

_HERE = os.path.dirname(__file__)
from agent_registry import AgentRegistry      # noqa: E402
from skill_registry import SkillRegistry      # noqa: E402
from intent_router import IntentRouter        # noqa: E402
from qa_history import QAHistory              # noqa: E402
from rollback_log import RollbackLog          # noqa: E402


class CompanyOS:
    def __init__(self, agents_seed: Optional[str] = None, skills_seed: Optional[str] = None,
                 qa_store: Optional[str] = None, rollback_store: Optional[str] = None):
        self.agents = AgentRegistry()
        self.skills = SkillRegistry()
        self.agents.load_seed(agents_seed or os.path.join(_HERE, "agents.registry.json"))
        self.skills.load_seed(skills_seed or os.path.join(_HERE, "skills.registry.json"))
        self.router = IntentRouter(self.agents, self.skills)
        self.qa = QAHistory(qa_store)
        self.rollback = RollbackLog(rollback_store)

    def handle(self, text: str) -> Dict:
        """Định tuyến 1 yêu cầu → quyết định (department, agent, skill) + ghi QA."""
        decision = self.router.route(text)
        resolved = bool(decision["agent_id"] and decision["skill_id"])
        self.qa.record("architecture", f"route:{decision['intent']}",
                       "PASS" if resolved else "FAIL",
                       meta={"agent": decision["agent_id"], "skill": decision["skill_id"]})
        return {**decision, "resolved": resolved}

    def qa_gate(self, gate: str, name: str, result: str, meta: Optional[Dict] = None) -> Dict:
        return self.qa.record(gate, name, result, meta)

    def record_rollback(self, target: str, reason: str, from_ver: str = "", to_ver: str = "") -> Dict:
        return self.rollback.record(target, reason, from_ver, to_ver)

    def status(self) -> Dict:
        return {"agents": self.agents.stats(), "skills": self.skills.stats(),
                "qa": self.qa.summary(), "rollbacks": len(self.rollback.list())}
