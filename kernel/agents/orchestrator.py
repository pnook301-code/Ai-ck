"""Orchestrator Agent - plans and coordinates multi-agent workflows"""
from typing import Any, Dict, List, Optional, Set
from .base import BaseAgent
from .types import AgentCapability, AgentTask


class OrchestratorAgent(BaseAgent):
    def __init__(self, agent_registry: Any = None, event_bus: Any = None, logger: Any = None):
        super().__init__(
            name="orchestrator",
            role="planner",
            capabilities={
                AgentCapability.PLAN,
                AgentCapability.COORDINATE,
                AgentCapability.REPORT,
            },
            event_bus=event_bus,
            logger=logger,
        )
        self.agent_registry = agent_registry
        self.plan_history: List[Dict] = []

    async def plan(self, objective: str) -> Dict[str, Any]:
        self._log_entry(f"Planning: {objective}")
        plan = {
            "id": f"plan_{len(self.plan_history) + 1}",
            "objective": objective,
            "steps": [],
            "status": "planning",
        }
        steps = self._analyze_objective(objective)
        plan["steps"] = steps
        plan["status"] = "ready"
        self.plan_history.append(plan)
        if self.event_bus:
            await self.event_bus.emit("orchestrator.plan.created", {
                "plan_id": plan["id"], "objective": objective, "steps": len(steps),
            })
        return plan

    def _analyze_objective(self, objective: str) -> List[Dict]:
        steps = []
        obj_lower = objective.lower()

        if any(w in obj_lower for w in ["code", "write", "create", "build", "implement", "develop"]):
            steps.extend([
                {"step": 1, "agent": "coder", "action": "implement", "description": "Write code"},
                {"step": 2, "agent": "reviewer", "action": "review", "description": "Review code quality"},
                {"step": 3, "agent": "tester", "action": "test", "description": "Run tests"},
            ])
        if any(w in obj_lower for w in ["test", "verify", "check", "validate"]):
            steps.append({"step": 1, "agent": "tester", "action": "test", "description": "Run tests"})
        if any(w in obj_lower for w in ["security", "audit", "vulnerability", "scan"]):
            steps.extend([
                {"step": 1, "agent": "security", "action": "audit", "description": "Security audit"},
                {"step": 2, "agent": "coder", "action": "fix", "description": "Fix vulnerabilities"},
            ])
        if any(w in obj_lower for w in ["deploy", "release", "ship", "production"]):
            steps.extend([
                {"step": 1, "agent": "tester", "action": "test", "description": "Final testing"},
                {"step": 2, "agent": "devops", "action": "deploy", "description": "Deploy to production"},
            ])
        if any(w in obj_lower for w in ["research", "find", "search", "investigate", "learn"]):
            steps.append({"step": 1, "agent": "researcher", "action": "research", "description": "Research topic"})
        if not steps:
            steps = [
                {"step": 1, "agent": "researcher", "action": "research", "description": "Research approach"},
                {"step": 2, "agent": "coder", "action": "implement", "description": "Implement solution"},
                {"step": 3, "agent": "tester", "action": "test", "description": "Verify solution"},
                {"step": 4, "agent": "reviewer", "action": "review", "description": "Final review"},
            ]
        return steps

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        self._log_entry(f"Executing plan: {plan['objective']}")
        results = []

        for step in plan["steps"]:
            agent_name = step["agent"]
            agent = self.agent_registry.get(agent_name) if self.agent_registry else None

            if not agent:
                results.append({
                    "step": step["step"], "status": "skipped",
                    "reason": f"Agent {agent_name} not available",
                })
                continue

            task = AgentTask(
                title=step["description"],
                description=f"Step {step['step']}: {step['action']} for {plan['objective']}",
                assigned_to=agent_name,
            )

            await self.send(agent_name, "task", task.to_dict() if hasattr(task, 'to_dict') else {}, task.id)
            task = await agent.execute(task)

            results.append({
                "step": step["step"], "agent": agent_name,
                "action": step["action"], "status": task.status, "result": task.result,
            })

        plan["status"] = "completed"
        plan["results"] = results
        if self.event_bus:
            await self.event_bus.emit("orchestrator.plan.completed", {
                "plan_id": plan["id"], "steps_completed": sum(1 for r in results if r["status"] == "completed"),
            })
        return plan

    async def delegate(self, agent_name: str, task_desc: str, priority: str = "medium") -> Dict:
        agent = self.agent_registry.get(agent_name) if self.agent_registry else None
        if not agent:
            return {"error": f"Agent {agent_name} not found"}
        task = AgentTask(
            title=task_desc, description=task_desc,
            priority=priority, assigned_to=agent_name,
        )
        await self.send(agent_name, "task", {}, task.id)
        task = await agent.execute(task)
        return task

    async def _do_task(self, task: AgentTask) -> Any:
        plan = await self.plan(task.description)
        result = await self.execute_plan(plan)
        return {"plan": result, "agents": self.agent_registry.get_all_status() if self.agent_registry else {}}
