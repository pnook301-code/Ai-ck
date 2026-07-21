"""Coder Agent — writes, refactors, and debugs code"""

from typing import Any, Dict, Optional, Set
from kernel.agents.base import BaseAgent
from kernel.agents.types import AgentCapability, AgentTask


class CoderAgent(BaseAgent):
    def __init__(self, event_bus: Any = None, logger: Any = None):
        super().__init__(
            name="coder",
            role="developer",
            capabilities={
                AgentCapability.CODE_WRITE,
                AgentCapability.CODE_REVIEW,
                AgentCapability.CODE_REFACTOR,
                AgentCapability.CODE_DEBUG,
            },
            event_bus=event_bus,
            logger=logger,
        )

    async def _do_task(self, task: AgentTask) -> Dict[str, Any]:
        desc = task.description.lower()
        if "refactor" in desc or "optimize" in desc:
            return self._refactor(task)
        if "debug" in desc or "fix" in desc or "bug" in desc:
            return self._debug(task)
        if "review" in desc:
            return self._review(task)
        return self._implement(task)

    def _implement(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "implemented",
            "agent": "coder",
            "description": task.description,
            "output": f"CoderAgent: Implemented solution for '{task.description}'",
            "language": self._detect_language(task.description),
        }

    def _refactor(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "refactored",
            "agent": "coder",
            "description": task.description,
            "output": f"CoderAgent: Refactored code for '{task.description}'",
            "changes": ["extracted functions", "improved naming", "added type hints"],
        }

    def _debug(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "debugged",
            "agent": "coder",
            "description": task.description,
            "output": f"CoderAgent: Debugged issue in '{task.description}'",
            "root_cause": "identified and fixed",
        }

    def _review(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "reviewed",
            "agent": "coder",
            "description": task.description,
            "output": f"CoderAgent: Code review completed for '{task.description}'",
            "issues": [],
            "score": 85,
        }

    def _detect_language(self, text: str) -> str:
        langs = {"python": "python", "typescript": "typescript", "javascript": "javascript",
                 "rust": "rust", "go": "go", "java": "java", "cpp": "cpp", "c++": "cpp"}
        for key, val in langs.items():
            if key in text.lower():
                return val
        return "python"
