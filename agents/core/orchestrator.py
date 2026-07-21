"""Orchestrator Agent - plans and coordinates all agents"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.core.base_agent import BaseAgent, AgentTask


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="orchestrator",
            role="planner",
            capabilities=["plan", "coordinate", "delegate", "review", "report"]
        )
        self.agents = {}
        self.tasks = []
        self.plan_history = []

    def register_agent(self, agent):
        self.agents[agent.name] = agent
        self._log(f"Registered agent: {agent.name} ({agent.role})")

    def plan(self, objective):
        self._log(f"Planning: {objective}")
        plan = {
            "id": f"plan_{len(self.plan_history)+1}",
            "objective": objective,
            "steps": [],
            "status": "planning"
        }

        # Analyze objective and create steps
        steps = self._analyze_objective(objective)
        plan["steps"] = steps
        plan["status"] = "ready"
        self.plan_history.append(plan)
        return plan

    def _analyze_objective(self, objective):
        steps = []
        obj_lower = objective.lower()

        # Code-related tasks
        if any(w in obj_lower for w in ["code", "write", "create", "build", "implement", "develop"]):
            steps.append({"step": 1, "agent": "coder", "action": "implement", "description": "Write code"})
            steps.append({"step": 2, "agent": "reviewer", "action": "review", "description": "Review code quality"})
            steps.append({"step": 3, "agent": "tester", "action": "test", "description": "Run tests"})

        # Test-related tasks
        if any(w in obj_lower for w in ["test", "verify", "check", "validate"]):
            steps.append({"step": 1, "agent": "tester", "action": "test", "description": "Run tests"})
            steps.append({"step": 2, "agent": "reviewer", "action": "review", "description": "Review results"})

        # Security tasks
        if any(w in obj_lower for w in ["security", "audit", "vulnerability", "scan"]):
            steps.append({"step": 1, "agent": "security", "action": "audit", "description": "Security audit"})
            steps.append({"step": 2, "agent": "coder", "action": "fix", "description": "Fix vulnerabilities"})

        # Deployment tasks
        if any(w in obj_lower for w in ["deploy", "release", "ship", "production"]):
            steps.append({"step": 1, "agent": "tester", "action": "test", "description": "Final testing"})
            steps.append({"step": 2, "agent": "devops", "action": "deploy", "description": "Deploy to production"})
            steps.append({"step": 3, "agent": "devops", "action": "monitor", "description": "Monitor deployment"})

        # Research tasks
        if any(w in obj_lower for w in ["research", "find", "search", "investigate", "learn"]):
            steps.append({"step": 1, "agent": "researcher", "action": "research", "description": "Research topic"})
            steps.append({"step": 2, "agent": "reviewer", "action": "review", "description": "Review findings"})

        # If no specific steps identified, create generic plan
        if not steps:
            steps = [
                {"step": 1, "agent": "researcher", "action": "research", "description": "Research approach"},
                {"step": 2, "agent": "coder", "action": "implement", "description": "Implement solution"},
                {"step": 3, "agent": "tester", "action": "test", "description": "Verify solution"},
                {"step": 4, "agent": "reviewer", "action": "review", "description": "Final review"}
            ]

        return steps

    def execute_plan(self, plan):
        self._log(f"Executing plan: {plan['objective']}")
        results = []

        for step in plan["steps"]:
            agent_name = step["agent"]
            if agent_name not in self.agents:
                results.append({"step": step["step"], "status": "skipped", "reason": f"Agent {agent_name} not available"})
                continue

            agent = self.agents[agent_name]
            task = AgentTask(
                title=step["description"],
                description=f"Step {step['step']}: {step['action']} for {plan['objective']}",
                assigned_to=agent_name
            )

            # Delegate to agent
            self.send(agent_name, "task", task.to_dict(), task.id)
            task = agent.execute(task)

            results.append({
                "step": step["step"],
                "agent": agent_name,
                "action": step["action"],
                "status": task.status,
                "result": task.result
            })

            # If step fails, continue but note it
            if task.status == "failed":
                self._log(f"Step {step['step']} failed: {task.result}")

        plan["status"] = "completed"
        plan["results"] = results
        return plan

    def delegate(self, agent_name, task_desc, priority="medium"):
        if agent_name not in self.agents:
            return {"error": f"Agent {agent_name} not found"}

        agent = self.agents[agent_name]
        task = AgentTask(
            title=task_desc,
            description=task_desc,
            priority=priority,
            assigned_to=agent_name
        )

        self.send(agent_name, "task", task.to_dict(), task.id)
        task = agent.execute(task)
        return task.to_dict()

    def get_all_agents(self):
        return {name: agent.get_status() for name, agent in self.agents.items()}

    def get_plan_history(self):
        return self.plan_history

    def _do_task(self, task):
        plan = self.plan(task.description)
        result = self.execute_plan(plan)
        return {
            "plan": result,
            "agents": self.get_all_agents()
        }
