"""Knowledge Pipeline — orchestrate extraction, graph population, and inference"""

from typing import Any, Dict, List, Optional
from kernel.memory.types import (
    KnowledgeUnit, KnowledgeRelation, EntityType, RelationType,
)
from kernel.memory.knowledge_graph import KnowledgeGraph
from .schema import KnowledgeSchema
from .extraction import EntityExtractor, RelationExtractor


class KnowledgePipeline:
    def __init__(self, graph: Optional[KnowledgeGraph] = None,
                 schema: Optional[KnowledgeSchema] = None):
        self.graph = graph or KnowledgeGraph()
        self.schema = schema or KnowledgeSchema()
        self.extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()

    def process_text(self, text: str, source: str = "pipeline",
                     run_inference: bool = True) -> Dict[str, Any]:
        entities = self.extractor.extract_from_text(text, source=source)

        entity_map = {}
        for entity in entities:
            eid = self.graph.add_entity(entity)
            entity_map[entity.name.lower()] = eid

        relations = self.relation_extractor.extract_from_text(
            text, source=source, existing_entities=entity_map,
        )
        co_occurrence = self.relation_extractor.extract_from_entities(entities)
        all_relations = relations + co_occurrence

        for rel in all_relations:
            self.graph.add_relation(rel)

        inferred = self.graph.infer() if run_inference else 0

        return {
            "entities_added": len(entities),
            "relations_added": len(all_relations),
            "inferences": inferred,
            "total_entities": self.graph.stats.total_entities,
            "total_relations": self.graph.stats.total_relations,
        }

    def process_agent_interaction(self, agent_name: str, action: str,
                                  target: str, outcome: str) -> Dict[str, Any]:
        agent_unit = KnowledgeUnit(
            name=agent_name, description=f"Agent: {agent_name}",
            entity_type=EntityType.AGENT, source="orchestrator",
            properties={"role": agent_name, "last_action": action},
        )
        agent_id = self.graph.add_entity(agent_unit)

        event_unit = KnowledgeUnit(
            name=f"{agent_name}_{action}",
            description=f"{agent_name} performed {action} on {target}",
            entity_type=EntityType.EVENT, source="orchestrator",
            properties={"action": action, "target": target, "outcome": outcome},
        )
        event_id = self.graph.add_entity(event_unit)

        self.graph.add_relation(KnowledgeRelation(
            source_id=agent_id, target_id=event_id,
            relation_type=RelationType.GENERATES,
        ))

        existing = self.graph.find_by_name(target)
        if existing:
            self.graph.add_relation(KnowledgeRelation(
                source_id=event_id, target_id=existing.id,
                relation_type=RelationType.REFERENCES,
                properties={"outcome": outcome},
            ))

        inferred = self.graph.infer()

        return {
            "agent_id": agent_id, "event_id": event_id,
            "inferences": inferred,
        }

    def query(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        entity = self.graph.find_by_name(entity_name)
        if not entity:
            return {"error": f"Entity '{entity_name}' not found"}
        subgraph = self.graph.get_subgraph({entity.id}, depth=depth)
        return {
            "entity": entity.to_dict(),
            "subgraph": subgraph,
            "stats": self.graph.stats,
        }

    def get_entity_context(self, entity_id: str,
                           max_depth: int = 2) -> Dict[str, Any]:
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found"}

        outgoing = self.graph.traverse(entity_id, max_depth=max_depth)
        incoming = self.graph.traverse(entity_id, max_depth=max_depth, direction="incoming")

        return {
            "entity": entity.to_dict(),
            "outgoing": [{"name": e.name, "relation": r, "weight": w}
                         for e, r, w in outgoing],
            "incoming": [{"name": e.name, "relation": r, "weight": w}
                         for e, r, w in incoming],
        }

    def suggest_connections(self, entity_id: str, threshold: float = 0.3) -> List[Dict]:
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return []

        suggestions = []
        outgoing_ids = set()
        for rel in self.graph.get_relations(entity_id):
            outgoing_ids.add(rel.target_id)

        for candidate_id, candidate in list(self.graph._entities.items()):
            if candidate_id == entity_id or candidate_id in outgoing_ids:
                continue
            if entity.entity_type == candidate.entity_type:
                suggestions.append({
                    "target": candidate.name,
                    "target_id": candidate.id,
                    "relation": "related_to",
                    "reason": f"Same type ({entity.entity_type.value})",
                    "confidence": 0.5,
                })

        return suggestions[:10]

    def save(self, path: str = ""):
        return self.graph.save(path)

    def load(self, path: str = "") -> bool:
        return self.graph.load(path)

    def status(self) -> Dict[str, Any]:
        stats = self.graph.stats
        return {
            "total_entities": stats.total_entities,
            "total_relations": stats.total_relations,
            "by_entity_type": stats.by_entity_type,
            "by_relation_type": stats.by_relation_type,
            "inferences": stats.total_inferences,
        }
