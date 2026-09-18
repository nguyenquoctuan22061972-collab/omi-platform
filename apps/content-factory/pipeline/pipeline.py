"""Content Pipeline state machine (PRD-009 E): Topic→Research→Script→Thumbnail→Video→QA→Publish.

Mock execution — mỗi bước trả kết quả giả lập, KHÔNG gọi API thật.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

STAGES = ["topic", "research", "script", "thumbnail", "video", "qa", "publish"]


class ContentPipeline:
    def __init__(self, topic: str):
        self.topic = topic
        self.index = 0
        self.state = "topic"
        self.history: List[Dict] = [{"stage": "topic", "status": "pending"}]
        self.artifacts: Dict[str, str] = {}

    def current(self) -> str:
        return self.state

    def is_done(self) -> bool:
        return self.state == "publish" and self.history[-1]["status"] == "done"

    def _mock_run(self, stage: str) -> str:
        return f"[mock:{stage}] {self.topic}"

    def advance(self, runner: Optional[Callable[[str], str]] = None) -> Dict:
        """Chạy stage hiện tại (mock), ghi artifact, chuyển stage kế."""
        run = runner or self._mock_run
        stage = STAGES[self.index]
        self.artifacts[stage] = run(stage)
        self.history[-1] = {"stage": stage, "status": "done"}
        if self.index < len(STAGES) - 1:
            self.index += 1
            self.state = STAGES[self.index]
            self.history.append({"stage": self.state, "status": "pending"})
        return {"stage": stage, "artifact": self.artifacts[stage], "next": self.state}

    def run_all(self, runner: Optional[Callable[[str], str]] = None) -> Dict:
        for _ in range(len(STAGES)):
            self.advance(runner)
            if self.is_done():
                break
        return {"topic": self.topic, "done": self.is_done(),
                "stages_completed": [h["stage"] for h in self.history if h["status"] == "done"],
                "artifacts": self.artifacts}
