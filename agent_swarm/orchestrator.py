"""
SwarmOrchestrator — ผู้ควบคุม Agent Swarm
รับงานใหญ่ → วิเคราะห์ → แบ่งงาน → แจกจ่าย → รวมผล
"""

import time
import uuid
import logging
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from .message_bus import EventBus, get_event_bus
from .shared_memory import SharedMemory, get_shared_memory
from .agents.base_agent import BaseAgent, AgentMessage
from .agents import create_all_agents
from core.vector_memory import get_vector_memory

logger = logging.getLogger("NEXUS-SwarmOrchestrator")


@dataclass
class SwarmTask:
    id: str = field(default_factory=lambda: f"swarm_{int(time.time())}_{str(uuid.uuid4())[:6]}")
    goal: str = ""
    steps: List[Dict] = field(default_factory=list)
    assignments: Dict[str, str] = field(default_factory=dict)  # agent_name → step
    results: Dict[str, str] = field(default_factory=dict)  # agent_name → result
    status: str = "pending"  # pending, planning, executing, synthesizing, done, failed
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    final_output: str = ""


class SwarmOrchestrator:
    """Orchestrator — accepts big tasks, breaks them down, distributes to agents, synthesizes results."""

    def __init__(self, max_workers: int = 6):
        self.event_bus = get_event_bus()
        self.memory = get_shared_memory()
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self._lock = threading.RLock()

    def start(self):
        """Start orchestrator and all agents."""
        self.running = True

        # Create and start all agents
        agent_instances = create_all_agents()
        for agent in agent_instances:
            agent.start()
            self.agents[agent.name] = agent

        # Register for events
        self.event_bus.on("swarm:submit", self._on_submit)
        self.event_bus.on("agent:response", self._on_agent_response)

        self.event_bus.start()

        logger.info(
            f"🚀 SwarmOrchestrator STARTED | "
            f"{len(self.agents)} agents ready | "
            f"Agents: {list(self.agents.keys())}"
        )

    def _on_submit(self, event):
        """Handle swarm:submit event."""
        goal = event.data.get("goal", "")
        if goal:
            self.submit(goal, event.data.get("context", {}))

    def _on_agent_response(self, event):
        """Handle agent:response event."""
        logger.info(f"Agent response: {event.sender} → {event.data.get('result', '')[:50]}")

    def stop(self):
        self.running = False
        for agent in self.agents.values():
            agent.stop()
        self.executor.shutdown(wait=True)
        self.event_bus.stop()
        logger.info("🛑 SwarmOrchestrator STOPPED")

    def submit(self, goal: str, context: Dict = None) -> str:
        """Submit a big goal. Orchestrator will plan and distribute."""
        task = SwarmTask(goal=goal)
        self.tasks[task.id] = task

        # Step 1: Plan
        task.status = "planning"
        plan = self._plan(goal, context or {})

        # Step 2: Assign
        task.steps = plan
        assignments = self._assign(plan)
        task.assignments = assignments

        # Step 3: Execute
        task.status = "executing"
        self._execute(task)

        return task.id

    def _plan(self, goal: str, context: Dict) -> List[Dict]:
        """Plan execution steps based on goal analysis."""
        steps = []
        goal_lower = goal.lower()

        # Auto-detect required agents based on goal
        if any(w in goal_lower for w in ["หา", "research", "search", "ค้นหา", "ข้อมูล"]):
            steps.append({"agent": "researcher", "step": f"Research: {goal}"})
        if any(w in goal_lower for w in ["เขียน", "code", "write", "สร้าง", "function", "api"]):
            steps.append({"agent": "coder", "step": f"Code: {goal}"})
        if any(w in goal_lower for w in ["เขียน", "write", "บทความ", "document", "สรุป"]):
            steps.append({"agent": "writer", "step": f"Write: {goal}"})
        if any(w in goal_lower for w in ["วิเคราะห์", "analyze", "data", "เปรียบเทียบ", "compare"]):
            steps.append({"agent": "analyst", "step": f"Analyze: {goal}"})
        if any(w in goal_lower for w in ["แปล", "translate", "language"]):
            steps.append({"agent": "translator", "step": f"Translate: {goal}"})
        if any(w in goal_lower for w in ["ไอเดีย", "idea", "brainstorm", "สร้างสรรค์", "design"]):
            steps.append({"agent": "creator", "step": f"Create: {goal}"})

        # For complex tasks, always include all agents for comprehensive analysis
        if len(steps) >= 2 or not steps:
            for name in self.agents:
                if name not in [s["agent"] for s in steps]:
                    steps.append({"agent": name, "step": f"Analyze from {name} perspective: {goal}"})

        return steps

    def _assign(self, steps: List[Dict]) -> Dict[str, str]:
        """Assign steps to agents."""
        assignments = {}
        for step in steps:
            agent_name = step["agent"]
            if agent_name in self.agents:
                assignments[agent_name] = step["step"]
        return assignments

    def _execute(self, task: SwarmTask):
        """Execute all assignments in parallel."""
        futures = {}
        for agent_name, step_text in task.assignments.items():
            agent = self.agents.get(agent_name)
            if agent:
                future = self.executor.submit(agent.work, step_text, {"task_id": task.id})
                futures[future] = agent_name

        # Collect results
        for future in as_completed(futures, timeout=60):
            agent_name = futures[future]
            try:
                result = future.result()
                task.results[agent_name] = result
                logger.info(f"✅ {agent_name} completed task for: {task.goal[:40]}")
            except Exception as e:
                task.results[agent_name] = f"ERROR: {e}"
                logger.error(f"❌ {agent_name} failed: {e}")

        # Synthesize
        task.status = "synthesizing"
        task.final_output = self._synthesize(task)
        task.status = "done"
        task.completed_at = time.time()

        # Save to shared memory
        self.memory.save(
            f"swarm_result_{task.id}",
            {"goal": task.goal, "results": task.results, "output": task.final_output},
            tags=["swarm", "result"],
        )
        # Save to vector memory
        vm = get_vector_memory()
        vm.add_document(
            f"Swarm Task: {task.goal}\n\n{task.final_output}",
            {"task_id": task.id, "type": "swarm_result"}
        )

        # Emit completion
        self.event_bus.emit("swarm:completed", {
            "task_id": task.id,
            "goal": task.goal,
            "output": task.final_output,
        })

    def _synthesize(self, task: SwarmTask) -> str:
        """Combine all agent results into final output."""
        parts = [f"🎯 Goal: {task.goal}\n"]
        parts.append(f"📊 Agents consulted: {len(task.results)}\n")

        for agent_name, result in task.results.items():
            parts.append(f"--- {agent_name.upper()} ---")
            parts.append(result)
            parts.append("")

        # Save synthesis
        parts.append(f"\n✅ Swarm completed in {len(task.results)} parallel agent calls")
        return "\n".join(parts)

    def get_status(self) -> Dict:
        with self._lock:
            vm = get_vector_memory()
            return {
                "running": self.running,
                "agents": {n: a.get_status() for n, a in self.agents.items()},
                "tasks_total": len(self.tasks),
                "tasks_done": sum(1 for t in self.tasks.values() if t.status == "done"),
                "tasks_running": sum(1 for t in self.tasks.values() if t.status == "executing"),
                "event_bus": self.event_bus.get_stats(),
                "memory": self.memory.get_stats(),
                "vector_memory": len(vm.documents),
            }

    def get_task(self, task_id: str) -> Optional[SwarmTask]:
        return self.tasks.get(task_id)


# Global instance
_swarm_orchestrator: Optional[SwarmOrchestrator] = None


def get_swarm_orchestrator() -> SwarmOrchestrator:
    global _swarm_orchestrator
    if _swarm_orchestrator is None:
        _swarm_orchestrator = SwarmOrchestrator()
    return _swarm_orchestrator
