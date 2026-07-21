"""Iterative Consensus Engine — multi-agent feedback loop with DoD gate"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable

from .types import IterationResult, ROLES
from .agents import ArchitectAgent, CriticAgent, JudgeAgent


class IterativeConsensusEngine:
    def __init__(self, event_bus=None, logger=None,
                 max_iterations: int = 20, judge_threshold: float = 85.0):
        self._event_bus = event_bus
        self._logger = logger
        self._max_iterations = max_iterations
        self._judge_threshold = judge_threshold
        self._agents = {
            ROLES.ARCHITECT: ArchitectAgent(event_bus=event_bus, logger=logger),
            ROLES.CRITIC: CriticAgent(event_bus=event_bus, logger=logger),
            ROLES.JUDGE: JudgeAgent(threshold=judge_threshold, event_bus=event_bus, logger=logger),
        }
        self._sandbox = None
        self.history: List[IterationResult] = []

    async def run(self, task: str, initial_code: str = "",
                  llm_callback: Optional[Callable] = None) -> Dict[str, Any]:
        iteration = 0
        current_code = initial_code
        previous_feedback = ""
        cumulative_scores: Dict[str, float] = {}
        self.history.clear()

        while iteration < self._max_iterations:
            iteration += 1
            current_role = ROLES.ORDER[(iteration - 1) % len(ROLES.ORDER)]

            context = {
                "task": task,
                "current_code": current_code,
                "previous_feedback": previous_feedback,
                "iteration": iteration,
                "history_summary": self._summarize_history(),
            }

            agent = self._agents[current_role]
            task_scores = cumulative_scores.copy()
            context_task = self._make_task(task, context, task_scores)
            agent_task = await agent.execute(context_task)
            response = agent_task.result or {}

            sandbox_result = None

            result = IterationResult(
                iteration=iteration,
                role=current_role,
                action=response.get("action", "evaluate"),
                content=response.get("output", ""),
                sandbox_result=sandbox_result,
                scores=response.get("scores", {}),
                decision=response.get("decision", "continue"),
                feedback=response.get("output", ""),
            )

            if current_role == ROLES.ARCHITECT and response.get("code"):
                current_code = response["code"]
            if response.get("scores"):
                cumulative_scores.update(response["scores"])

            self.history.append(result)

            if self._event_bus:
                await self._event_bus.emit("ice.iteration_complete", {
                    "iteration": iteration, "role": current_role,
                    "decision": result.decision,
                })

            if result.decision == "TERMINATE_LOOP":
                break

            previous_feedback = result.feedback

        return self._generate_final_report(task, current_code)

    def _make_task(self, task: str, context: Dict, scores: Dict[str, float] = None) -> Any:
        from kernel.agents.types import AgentTask
        return AgentTask(
            title=f"ICE iteration {context['iteration']}",
            description=f"{task}. Context: {json.dumps({k:v for k,v in context.items() if k != 'current_code'})}",
            metadata={"scores": scores or {}, "context": context},
        )

    def _summarize_history(self) -> str:
        if not self.history:
            return "No previous iterations."
        lines = []
        for r in self.history[-3:]:
            lines.append(f"Round {r.iteration} ({r.role}): {r.feedback[:100]}")
        return "\n".join(lines)

    def _generate_final_report(self, task: str, final_code: str) -> Dict[str, Any]:
        passed = any(r.decision == "TERMINATE_LOOP" and r.role == ROLES.JUDGE for r in self.history)
        last = self.history[-1] if self.history else None
        return {
            "success": passed,
            "task": task,
            "total_iterations": len(self.history),
            "final_code": final_code,
            "final_scores": last.scores if last else {},
            "history": [r.__dict__ for r in self.history],
            "recommendation": "READY_FOR_DEPLOYMENT" if passed else "NEEDS_MORE_WORK",
        }
