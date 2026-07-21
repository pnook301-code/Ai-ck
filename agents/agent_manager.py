"""Agent Manager - manages all agents and their workflows"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.core.base_agent import AgentTask
from agents.core.orchestrator import OrchestratorAgent
from agents.specialists.coder_agent import CoderAgent
from agents.specialists.tester_agent import TesterAgent
from agents.specialists.devops_agent import DevOpsAgent
from agents.specialists.researcher_agent import ResearcherAgent
from agents.specialists.security_agent import SecurityAgent
from agents.specialists.reviewer_agent import ReviewerAgent


class AgentManager:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.agents = {}
        self.workflow_log = []
        self._init_agents()

    def _init_agents(self):
        agent_classes = [
            CoderAgent,
            TesterAgent,
            DevOpsAgent,
            ResearcherAgent,
            SecurityAgent,
            ReviewerAgent
        ]

        for AgentClass in agent_classes:
            agent = AgentClass()
            self.agents[agent.name] = agent
            self.orchestrator.register_agent(agent)

        self._log(f"Initialized {len(self.agents)} agents")

    def _log(self, entry):
        self.workflow_log.append({
            "time": datetime.now().isoformat(),
            "entry": entry
        })

    def execute(self, objective):
        self._log(f"Executing objective: {objective}")

        # Plan
        plan = self.orchestrator.plan(objective)

        # Execute plan
        result = self.orchestrator.execute_plan(plan)

        # Compile report
        report = self._compile_report(objective, plan, result)
        self._log(f"Execution complete: {objective}")

        return report

    def delegate(self, agent_name, task_desc, priority="medium"):
        self._log(f"Delegating to {agent_name}: {task_desc}")
        return self.orchestrator.delegate(agent_name, task_desc, priority)

    def _compile_report(self, objective, plan, result):
        steps = result.get("results", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")
        failed = sum(1 for s in steps if s.get("status") == "failed")

        report = {
            "objective": objective,
            "plan_id": plan.get("id"),
            "summary": {
                "total_steps": len(steps),
                "completed": completed,
                "failed": failed,
                "success_rate": f"{(completed/len(steps)*100):.0f}%" if steps else "0%"
            },
            "steps": steps,
            "agent_status": self.get_all_agent_status(),
            "timestamp": datetime.now().isoformat()
        }
        return report

    def get_all_agent_status(self):
        return {name: agent.get_status() for name, agent in self.agents.items()}

    def get_agent(self, name):
        return self.agents.get(name)

    def get_workflow_log(self):
        return self.workflow_log

    def get_status(self):
        return {
            "agents": len(self.agents),
            "agent_names": list(self.agents.keys()),
            "orchestrator": self.orchestrator.get_status(),
            "workflow_entries": len(self.workflow_log)
        }

    def run_full_audit(self):
        self._log("Running full system audit")

        tasks = [
            ("security", "Run security audit on entire codebase"),
            ("tester", "Run all tests"),
            ("reviewer", "Quality check all code"),
            ("researcher", "Research and recommend improvements"),
            ("devops", "Check system health and deployment status")
        ]

        results = []
        for agent_name, task_desc in tasks:
            result = self.delegate(agent_name, task_desc)
            results.append(result)

        return {
            "audit_type": "full",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
