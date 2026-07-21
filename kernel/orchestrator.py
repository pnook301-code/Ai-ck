"""Unified OrchestratorEngine — connects Kernel + Agents + Functions + Memory + Knowledge Graph + Video"""

import time
from typing import Any, Dict, List, Optional, Callable
from kernel.events import EventBus, Event
from kernel.memory import MemoryOS, MemoryUnit, MemoryType, MemoryPriority
from kernel.memory.knowledge_graph import KnowledgeGraph
from kernel.memory.types import (
    KnowledgeUnit, KnowledgeRelation, EntityType, RelationType,
)
from kernel.fn import FunctionRegistry, register_all_categories
from kernel.agents import BaseAgent, AgentManager, OrchestratorAgent, AgentRegistry
from kernel.agents.specialists import (
    CoderAgent, TesterAgent, DevOpsAgent,
    ResearcherAgent, SecurityAgent, ReviewerAgent,
)
from knowledge.pipeline import KnowledgePipeline
from kernel.video.analyzer import VideoAnalyzer
from kernel.video.plugin import WatchPlugin


class OrchestratorEngine:
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()
        self.memory = MemoryOS()
        self.knowledge = KnowledgeGraph()
        self.knowledge_pipeline = KnowledgePipeline(graph=self.knowledge)
        self.fn_registry = FunctionRegistry()
        self.agent_registry = AgentRegistry()
        self.agent_manager = AgentManager()
        self.orchestrator = OrchestratorAgent(
            agent_registry=self.agent_registry,
            event_bus=self.event_bus,
        )
        self.video_analyzer = VideoAnalyzer()
        self.watch_plugin = WatchPlugin(analyzer=self.video_analyzer)
        self._watch_results: Dict[str, Any] = {}

        self._register_default_agents()
        self._setup_events()

    def _register_default_agents(self):
        agents = [
            CoderAgent(event_bus=self.event_bus),
            TesterAgent(event_bus=self.event_bus),
            DevOpsAgent(event_bus=self.event_bus),
            ResearcherAgent(event_bus=self.event_bus),
            SecurityAgent(event_bus=self.event_bus),
            ReviewerAgent(event_bus=self.event_bus),
        ]
        for agent in agents:
            self.register_agent(agent)

    def _setup_events(self):
        self.event_bus.on("memory.remember", self._on_remember)
        self.event_bus.on("memory.recall", self._on_recall)
        self.event_bus.on("fn.execute", self._on_fn_execute)
        self.event_bus.on("agent.delegate", self._on_agent_delegate)
        self.event_bus.on("kg.add_entity", self._on_kg_add_entity)
        self.event_bus.on("kg.add_relation", self._on_kg_add_relation)
        self.event_bus.on("kg.query", self._on_kg_query)
        self.event_bus.on("video.watch", self._on_video_watch)

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

    async def _on_kg_add_entity(self, event: Event):
        name = event.data.get("name", "")
        desc = event.data.get("description", "")
        etype = EntityType(event.data.get("entity_type", "concept"))
        entity = KnowledgeUnit(name=name, description=desc, entity_type=etype)
        self.knowledge.add_entity(entity)
        await self.event_bus.emit("kg.entity.added", {"entity_id": entity.id})

    async def _on_kg_add_relation(self, event: Event):
        src = event.data.get("source_id", "")
        tgt = event.data.get("target_id", "")
        rtype = RelationType(event.data.get("relation_type", "related_to"))
        rel = KnowledgeRelation(source_id=src, target_id=tgt, relation_type=rtype)
        self.knowledge.add_relation(rel)
        await self.event_bus.emit("kg.relation.added", {"source": src, "target": tgt})

    async def _on_kg_query(self, event: Event):
        name = event.data.get("name", "")
        entity = self.knowledge.find_by_name(name)
        result = entity.to_dict() if entity else {"error": "not found"}
        await self.event_bus.emit("kg.query.result", result)

    async def _on_video_watch(self, event: Event):
        params = event.data
        result = self.watch_plugin.execute(params, llm_callback=None)
        self._watch_results[result.id] = result
        await self.event_bus.emit("video.watch.complete", {"result_id": result.id, "summary": result.summary})

    def bootstrap(self):
        register_all_categories(self.fn_registry)

    def register_agent(self, agent: BaseAgent):
        self.agent_registry.register(agent)
        self.agent_manager.register_agent(agent)

    async def process(self, input_text: str, source: str = "user") -> Dict[str, Any]:
        watch_params = self.watch_plugin.parse(input_text)
        if watch_params:
            return await self._process_watch(input_text, watch_params, source)

        ep_unit = self.memory.remember(input_text, MemoryType.EPISODIC,
                                        tags=["input", source], source=source)

        extraction = self.knowledge_pipeline.process_text(input_text, source=source)

        plan = await self.orchestrator.plan(input_text)
        results = []

        self.memory.remember(f"Plan: {plan['objective']}", MemoryType.SEMANTIC,
                             tags=["plan"], source="orchestrator")

        knowledge_context = self._get_knowledge_context(input_text)
        memory_hits = self.memory.recall(input_text, top_k=3)

        for step in plan["steps"]:
            agent_name = step["agent"]
            task_desc = step["description"]
            result = await self.agent_manager.delegate(agent_name, task_desc)

            self.knowledge_pipeline.process_agent_interaction(
                agent_name, step["action"], task_desc,
                str(result.status) if hasattr(result, 'status') else "completed",
            )

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
            "knowledge_stats": self.knowledge.stats,
        })

        return {
            "input": input_text,
            "plan": plan,
            "results": results,
            "memory": self.memory.to_dict(),
            "knowledge": {
                "extraction": extraction,
                "total_entities": self.knowledge.stats.total_entities,
                "total_relations": self.knowledge.stats.total_relations,
                "inferences": self.knowledge.stats.total_inferences,
            },
            "output": f"Processed '{input_text}': {len(results)} steps, "
                      f"{self.memory.stats.total_units} memory units, "
                      f"{self.knowledge.stats.total_entities} knowledge entities",
        }

    def _get_knowledge_context(self, text: str) -> Dict[str, Any]:
        words = [w.lower() for w in text.split() if len(w) > 3]
        related = []
        for word in words[:10]:
            entity = self.knowledge.find_by_name(word)
            if entity:
                subgraph = self.knowledge.get_subgraph({entity.id}, depth=1)
                related.append(subgraph)
        return {"related_entities": related[:5]}

    async def _process_watch(self, input_text: str, params: Dict[str, Any], source: str) -> Dict[str, Any]:
        ep_unit = self.memory.remember(input_text, MemoryType.EPISODIC,
                                        tags=["input", source, "video.watch"], source=source)

        entity = KnowledgeUnit(
            name=params["source"], description=f"Video: {params['query']}",
            entity_type=EntityType.DOCUMENT,
            properties={"query": params["query"], "source_type": params["source_type"].value},
        )
        self.knowledge.add_entity(entity)

        result = self.watch_plugin.execute(params, llm_callback=None)
        self._watch_results[result.id] = result

        if result.meta:
            self.memory.remember(
                f"Video: {result.meta.title} — {result.keyframes_extracted} keyframes, "
                f"{len(result.transcript.segments) if result.transcript else 0} transcript segments",
                MemoryType.SEMANTIC,
                tags=["video", params["source_type"].value],
                source="video_analyzer",
            )
        if result.error:
            self.memory.remember(
                f"Video error: {result.error}",
                MemoryType.EPISODIC,
                tags=["video", "error"],
                source="video_analyzer",
            )

        await self.event_bus.emit("orchestrator.video.complete", {
            "result_id": result.id, "source": params["source"],
            "summary": result.summary,
        })

        return {
            "input": input_text,
            "plan": {"objective": f"Analyze video: {params['query']}", "steps": []},
            "results": [{"agent": "video_analyzer", "task": params["query"],
                         "status": "completed" if not result.error else "error"}],
            "memory": self.memory.to_dict(),
            "knowledge": {
                "extraction": {},
                "total_entities": self.knowledge.stats.total_entities,
                "total_relations": self.knowledge.stats.total_relations,
                "inferences": self.knowledge.stats.total_inferences,
            },
            "video": result.summary,
            "output": f"Video analysis: {result.keyframes_extracted} keyframes extracted, "
                      f"{len(result.transcript.segments) if result.transcript else 0} transcript segments"
                      + (f" — error: {result.error}" if result.error else ""),
        }

    def get_video_result(self, result_id: str):
        return self._watch_results.get(result_id)

    def get_status(self) -> Dict[str, Any]:
        return {
            "memory": self.memory.to_dict(),
            "knowledge": self.knowledge.stats,
            "functions": self.fn_registry.get_stats(),
            "agents": self.agent_manager.get_status(),
        }
