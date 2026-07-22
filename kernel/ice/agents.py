"""ICE agents — Architect, Critic, Judge"""

from typing import Any, Dict
from kernel.agents.base import BaseAgent
from kernel.agents.types import AgentCapability, AgentTask


class ArchitectAgent(BaseAgent):
    def __init__(self, event_bus=None, logger=None):
        super().__init__(
            name="architect",
            role="architect",
            capabilities={AgentCapability.CODE_WRITE, AgentCapability.CODE_REVIEW, AgentCapability.PLAN},
            event_bus=event_bus, logger=logger,
        )

    async def _do_task(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "designed",
            "agent": "architect",
            "description": task.description,
            "output": f"Architect: Analyzed requirements for '{task.description}'",
            "code": "",
            "design": {"pattern": "clean_architecture", "components": [], "interfaces": []},
        }


class CriticAgent(BaseAgent):
    def __init__(self, event_bus=None, logger=None):
        super().__init__(
            name="critic",
            role="critic",
            capabilities={AgentCapability.CODE_REVIEW, AgentCapability.REVIEW, AgentCapability.REPORT},
            event_bus=event_bus, logger=logger,
        )

    async def _do_task(self, task: AgentTask) -> Dict[str, Any]:
        scores = {"architecture": 85, "security": 80, "performance": 82, "test_coverage": 78, "overall": 81}
        return {
            "status": "reviewed",
            "agent": "critic",
            "description": task.description,
            "output": f"Critic: Reviewed code for '{task.description}'",
            "scores": scores,
            "issues": [],
            "recommendations": [],
        }


class JudgeAgent(BaseAgent):
    def __init__(self, threshold: float = 85.0, event_bus=None, logger=None):
        super().__init__(
            name="judge",
            role="judge",
            capabilities={AgentCapability.REPORT, AgentCapability.REVIEW},
            event_bus=event_bus, logger=logger,
        )
        self._threshold = threshold
        self._iteration_count = 0
        self._max_iterations = 20

    async def _do_task(self, task: AgentTask) -> Dict[str, Any]:
        scores = task.metadata.get("scores", {})
        overall = scores.get("overall", 0)
        self._iteration_count += 1

        passed = overall >= self._threshold
        terminate = passed or self._iteration_count >= self._max_iterations

        return {
            "status": "judged",
            "agent": "judge",
            "score": overall,
            "threshold": self._threshold,
            "passed": passed,
            "decision": "TERMINATE_LOOP" if terminate else "continue",
            "output": f"Judge: {'PASSED' if passed else 'NOT PASSED'} (score={overall}, threshold={self._threshold})",
        }
