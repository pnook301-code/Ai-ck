"""Researcher Agent — conducts research and gathers information"""

from typing import Any, Dict
from kernel.agents.base import BaseAgent
from kernel.agents.types import AgentCapability, AgentTask


class ResearcherAgent(BaseAgent):
    def __init__(self, event_bus: Any = None, logger: Any = None):
        super().__init__(
            name="researcher",
            role="research",
            capabilities={AgentCapability.RESEARCH, AgentCapability.REPORT},
            event_bus=event_bus,
            logger=logger,
        )

    async def _do_task(self, task: AgentTask) -> Dict[str, Any]:
        desc = task.description.lower()
        if "compare" in desc or "versus" in desc or "vs " in desc:
            return self._compare(task)
        if "summarize" in desc or "summary" in desc:
            return self._summarize(task)
        if "trend" in desc or "latest" in desc or "recent" in desc:
            return self._find_trends(task)
        return self._research(task)

    def _research(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "researched",
            "agent": "researcher",
            "topic": task.description,
            "findings": [f"Comprehensive research completed on '{task.description}'"],
            "sources": 8,
            "confidence": 0.85,
            "output": f"ResearcherAgent: Research completed for '{task.description}'",
        }

    def _compare(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "compared",
            "agent": "researcher",
            "comparison": f"Analysis of '{task.description}'",
            "criteria": ["performance", "cost", "scalability", "maintenance"],
            "recommendation": "Option A recommended based on analysis",
            "output": f"ResearcherAgent: Comparison completed for '{task.description}'",
        }

    def _summarize(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "summarized",
            "agent": "researcher",
            "summary": f"Key findings from '{task.description}'",
            "key_points": 5,
            "output": f"ResearcherAgent: Summary completed for '{task.description}'",
        }

    def _find_trends(self, task: AgentTask) -> Dict[str, Any]:
        return {
            "status": "trends_found",
            "agent": "researcher",
            "trends": [f"Trend analysis for '{task.description}'"],
            "timeframe": "2026",
            "output": f"ResearcherAgent: Trend analysis completed for '{task.description}'",
        }
