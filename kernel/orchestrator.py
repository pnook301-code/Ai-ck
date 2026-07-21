"""Unified OrchestratorEngine — connects Kernel + Agents + Functions + Memory"""

import time
from typing import Any, Dict, List, Optional, Callable
from kernel.events import EventBus, Event
from kernel.memory import MemoryOS, MemoryUnit, MemoryType, MemoryPriority
from kernel.fn import FunctionRegistry, register_all_categories
from kernel.agents import BaseAgent, AgentManager, OrchestratorAgent, AgentRegistry


class OrchestratorEngine:
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()
        self.memory = MemoryOS()
        self.fn_registry = FunctionRegistry()
        self.agent_registry = AgentRegistry()
        self.agent_manager = AgentManager()
        self.orchestrator = OrchestratorAgent(
            agent_registry=self.agent_registry,
            event_bus=self.event_bus,
        )

        self._setup_events()

    def _setup_events(self):
        self.event_bus.on("memory.remember", self._on_remember)
        self.event_bus.on("memory.recall", self._on_recall)
        self.event_bus.on("fn.execute", self._on_fn_execute)
        self.event_bus.on("agent.delegate", self._on_agent_delegate)

    async def _on_remember(self, event: Event):
        content = event.data.get("content", "")
        mem_type = MemoryType(event.data.get("type", "episodic"))
        tags = event.data.get("tags", [])
        unit = self.memory.remember(content, mem_type, tags=tags)
        await self.event_bus.emit("memory.remembered", {"unit_id": unit.id})

    async def _on_recall(self, event: Event):
        query = event.data.get("query", "")
        results = self.memory.recall(query)
        await self.event_bus.emit("memory.recalled", {"results": [u.to_dict() for u in results]})

    async def _on_fn_execute(self, event: Event):
        fn_id = event.data.get("fn_id", "")
        params = event.data.get("params", {})
        result = await self.fn_registry.execute(fn_id, params)
        await self.event_bus.emit("fn.executed", {"fn_id": fn_id, "result": result.output})

    async def _on_agent_delegate(self, event: Event):
        agent_name = event.data.get("agent_name", "")
        task_desc = event.data.get("task", "")
        result = await self.agent_manager.delegate(agent_name, task_desc)
        await self.event_bus.emit("agent.delegated", {"agent": agent_name, "result": result})

    def bootstrap(self):
        register_all_categories(self.fn_registry)

    def register_agent(self, agent: BaseAgent):
        self.agent_registry.register(agent)
        self.agent_manager.register_agent(agent)

    async def process(self, input_text: str, source: str = "user") -> Dict[str, Any]:
        self.memory.remember(input_text, MemoryType.EPISODIC,
                             tags=["input", source], source=source)

        plan = await self.orchestrator.plan(input_text)
        results = []

        self.memory.remember(f"Plan: {plan['objective']}", MemoryType.SEMANTIC,
                             tags=["plan"], source="orchestrator")

        memory_hits = self.memory.recall(input_text, top_k=3)
        if memory_hits:
            pass

        for step in plan["steps"]:
            agent_name = step["agent"]
            task_desc = step["description"]
            result = await self.agent_manager.delegate(agent_name, task_desc)

            if isinstance(result, dict) and "error" in result:
                status = "skipped"
            else:
                status = result.status if isinstance(result.status, str) else result.status.value

            step_result = {"agent": agent_name, "task": task_desc, "status": status}
            results.append(step_result)

            self.memory.remember(
                f"{agent_name}: {task_desc} -> {status}",
                MemoryType.EPISODIC,
                tags=[agent_name, "execution", status],
                source="agent",
            )

        await self.event_bus.emit("orchestrator.cycle.complete", {
            "input": input_text,
            "steps": len(results),
            "memory_stats": self.memory.stats.total_units,
        })

        return {
            "input": input_text,
            "plan": plan,
            "results": results,
            "memory": self.memory.to_dict(),
            "output": f"Processed '{input_text}': {len(results)} steps, {self.memory.stats.total_units} memory units",
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "memory": self.memory.to_dict(),
            "functions": self.fn_registry.get_stats(),
            "agents": self.agent_manager.get_status(),
        }
