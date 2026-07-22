"""Agent Manager - manages agent lifecycle and workflow execution"""
import time
from typing import Any, Dict, List, Optional
from .registry import AgentRegistry
from .orchestrator import OrchestratorAgent
from .base import BaseAgent


class AgentManager:
    def __init__(self, agent_registry: AgentRegistry = None, orchestrator: OrchestratorAgent = None, logger: Any = None):
        self.registry = agent_registry or AgentRegistry(logger=logger)
        self.orchestrator = orchestrator or OrchestratorAgent(
            agent_registry=self.registry, logger=logger,
        )
        self.logger = logger
        self.workflow_log: List[Dict] = []

    def register_agent(self, agent: BaseAgent):
        self.registry.register(agent)
        self._log(f"Registered: {agent.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self.registry.get(name)

    def get_all_agents(self) -> List[BaseAgent]:
        return self.registry.list_agents()

    async def execute(self, objective: str) -> Dict[str, Any]:
        self._log(f"Execute: {objective}")
        plan = await self.orchestrator.plan(objective)
        result = await self.orchestrator.execute_plan(plan)
        report = self._compile_report(objective, plan, result)
        self._log(f"Complete: {objective}")
        return report

    async def delegate(self, agent_name: str, task_desc: str, priority: str = "medium") -> Dict:
        self._log(f"Delegate to {agent_name}: {task_desc}")
        return await self.orchestrator.delegate(agent_name, task_desc, priority)

    def _compile_report(self, objective: str, plan: Dict, result: Dict) -> Dict:
        steps = result.get("results", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")
        failed = sum(1 for s in steps if s.get("status") == "failed")
        return {
            "objective": objective,
            "plan_id": plan.get("id"),
            "summary": {
                "total_steps": len(steps),
                "completed": completed,
                "failed": failed,
                "success_rate": f"{(completed / len(steps) * 100):.0f}%" if steps else "0%",
            },
            "steps": steps,
            "agent_status": self.registry.get_all_status(),
        }

    def _log(self, entry: str):
        self.workflow_log.append({"time": time.time(), "entry": entry})

    def get_status(self) -> Dict[str, Any]:
        return {
            "agents": self.registry.count(),
            "agent_names": self.registry.get_names(),
            "workflow_entries": len(self.workflow_log),
        }
