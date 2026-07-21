"""Knowledge Graph engine — typed entity/relation store with inference and persistence"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from collections import defaultdict
from dataclasses import dataclass, field

from .types import (
    KnowledgeUnit, KnowledgeRelation, KnowledgeGraphStats,
    EntityType, RelationType, InferenceRule,
)


class KnowledgeGraph:
    def __init__(self, persistence_path: str = ""):
        self._entities: Dict[str, KnowledgeUnit] = {}
        self._relations: Dict[str, List[KnowledgeRelation]] = {}
        self._incoming: Dict[str, List[KnowledgeRelation]] = {}
        self._inference_count = 0
        self._rules: List[InferenceRule] = []
        self._persistence_path = persistence_path
        self._alias_index: Dict[str, str] = {}
        self._type_index: Dict[str, Set[str]] = defaultdict(set)

        self._register_default_rules()

    def _register_default_rules(self):
        self._rules = [
            InferenceRule(
                "transitive_depends",
                ["A depends_on B", "B depends_on C"],
                "A depends_on C",
            ),
            InferenceRule(
                "transitive_part_of",
                ["A part_of B", "B part_of C"],
                "A part_of C",
            ),
            InferenceRule(
                "transitive_contains",
                ["A contains B", "B contains C"],
                "A contains C",
            ),
            InferenceRule(
                "causation_chain",
                ["A causes B", "B causes C"],
                "A causes C",
            ),
            InferenceRule(
                "creates_uses",
                ["A creates B", "B uses C"],
                "A uses C",
            ),
            InferenceRule(
                "derived_knowledge",
                ["A derived_from B", "B derived_from C"],
                "A derived_from C",
            ),
        ]

    @property
    def stats(self) -> KnowledgeGraphStats:
        by_entity = defaultdict(int)
        for entity in self._entities.values():
            by_entity[entity.entity_type.value] += 1
        by_relation = defaultdict(int)
        for rels in self._relations.values():
            for r in rels:
                by_relation[r.relation_type.value] += 1
        return KnowledgeGraphStats(
            total_entities=len(self._entities),
            total_relations=sum(len(v) for v in self._relations.values()),
            by_entity_type=dict(by_entity),
            by_relation_type=dict(by_relation),
            total_inferences=self._inference_count,
        )

    def add_entity(self, unit: KnowledgeUnit) -> str:
        self._entities[unit.id] = unit
        self._type_index[unit.entity_type.value].add(unit.id)
        if unit.aliases:
            for alias in unit.aliases:
                self._alias_index[alias.lower()] = unit.id
        if unit.name:
            self._alias_index[unit.name.lower()] = unit.id
        return unit.id

    def get_entity(self, entity_id: str) -> Optional[KnowledgeUnit]:
        return self._entities.get(entity_id)

    def find_by_name(self, name: str) -> Optional[KnowledgeUnit]:
        eid = self._alias_index.get(name.lower())
        return self._entities.get(eid) if eid else None

    def find_by_type(self, entity_type: EntityType) -> List[KnowledgeUnit]:
        ids = self._type_index.get(entity_type.value, set())
        return [self._entities[eid] for eid in ids if eid in self._entities]

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id not in self._entities:
            return False
        entity = self._entities[entity_id]
        self._type_index[entity.entity_type.value].discard(entity_id)
        for alias in [entity.name.lower()] + [a.lower() for a in entity.aliases]:
            self._alias_index.pop(alias, None)
        del self._entities[entity_id]
        self._relations.pop(entity_id, None)
        self._incoming.pop(entity_id, None)
        for rels in self._relations.values():
            rels[:] = [r for r in rels if r.target_id != entity_id]
        for rels in self._incoming.values():
            rels[:] = [r for r in rels if r.source_id != entity_id]
        return True

    def add_relation(self, relation: KnowledgeRelation) -> bool:
        if relation.source_id not in self._entities:
            return False
        if relation.target_id not in self._entities:
            return False
        self._relations.setdefault(relation.source_id, []).append(relation)
        self._incoming.setdefault(relation.target_id, []).append(relation)
        return True

    def get_relations(self, entity_id: str,
                      relation_type: Optional[RelationType] = None,
                      direction: str = "outgoing") -> List[KnowledgeRelation]:
        if direction == "outgoing":
            rels = self._relations.get(entity_id, [])
        else:
            rels = self._incoming.get(entity_id, [])
        if relation_type:
            return [r for r in rels if r.relation_type == relation_type]
        return rels

    def query(self, source_type: Optional[EntityType] = None,
              target_type: Optional[EntityType] = None,
              relation_type: Optional[RelationType] = None,
              max_results: int = 50) -> List[Tuple[KnowledgeUnit, KnowledgeRelation, KnowledgeUnit]]:
        results = []
        for src_id, rels in self._relations.items():
            src = self._entities.get(src_id)
            if not src:
                continue
            if source_type and src.entity_type != source_type:
                continue
            for rel in rels:
                if relation_type and rel.relation_type != relation_type:
                    continue
                tgt = self._entities.get(rel.target_id)
                if not tgt:
                    continue
                if target_type and tgt.entity_type != target_type:
                    continue
                results.append((src, rel, tgt))
                if len(results) >= max_results:
                    return results
        return results

    def traverse(self, start_id: str, relation_type: Optional[RelationType] = None,
                 max_depth: int = 3, direction: str = "outgoing",
                 min_confidence: float = 0.0) -> List[Tuple[KnowledgeUnit, str, float]]:
        results = []
        visited = {start_id}
        queue = [(start_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            rels = (self._relations.get(current, []) if direction == "outgoing"
                    else self._incoming.get(current, []))
            for rel in rels:
                if relation_type and rel.relation_type != relation_type:
                    continue
                next_id = rel.target_id if direction == "outgoing" else rel.source_id
                if next_id not in visited:
                    visited.add(next_id)
                    node = self._entities.get(next_id)
                    if node and node.confidence >= min_confidence:
                        results.append((node, rel.relation_type.value, rel.weight))
                    queue.append((next_id, depth + 1))
        return results

    def find_path(self, from_id: str, to_id: str,
                  max_depth: int = 5) -> List[List[KnowledgeRelation]]:
        paths = []
        def _dfs(current, target, path, visited):
            if len(path) > max_depth:
                return
            if current == target:
                paths.append(list(path))
                return
            for rel in self._relations.get(current, []):
                if rel.target_id not in visited:
                    visited.add(rel.target_id)
                    path.append(rel)
                    _dfs(rel.target_id, target, path, visited)
                    path.pop()
                    visited.discard(rel.target_id)
        _dfs(from_id, to_id, [], {from_id})
        return paths

    def infer(self) -> int:
        inferred = 0
        for _ in range(3):
            for rule in self._rules:
                inferred += self._apply_rule(rule)
        self._inference_count += inferred
        return inferred

    def _apply_rule(self, rule: InferenceRule) -> int:
        count = 0
        ant0 = rule.antecedent[0].lower().replace("_", " ")
        ant1 = rule.antecedent[1].lower().replace("_", " ") if len(rule.antecedent) > 1 else ""
        for src_id, src in list(self._entities.items()):
            for rel in self._relations.get(src_id, []):
                if rel.relation_type.value.replace("_", " ") not in ant0:
                    continue
                mid = rel.target_id
                mid_entity = self._entities.get(mid)
                if not mid_entity:
                    continue
                for rel2 in self._relations.get(mid, []):
                    if rel2.relation_type.value.replace("_", " ") not in ant1:
                        continue
                    tgt_id = rel2.target_id
                    if tgt_id == src_id:
                        continue

                    consequent_rel = rule.consequent.split()[1] if len(rule.consequent.split()) >= 3 else "related_to"
                    exists = False
                    for existing in self._relations.get(src_id, []):
                        if existing.target_id == tgt_id and existing.relation_type.value.replace("_", " ") == consequent_rel.replace("_", " "):
                            exists = True
                            break

                    if not exists:
                        new_rel = KnowledgeRelation(
                            source_id=src_id,
                            target_id=tgt_id,
                            relation_type=RelationType.RELATED_TO,
                            weight=rel.weight * rel2.weight * rule.confidence,
                            properties={"inferred": True, "rule": rule.name},
                        )
                        for rt in RelationType:
                            if rt.value.replace("_", " ") == consequent_rel.replace("_", " "):
                                new_rel.relation_type = rt
                                break
                        self._relations.setdefault(src_id, []).append(new_rel)
                        self._incoming.setdefault(tgt_id, []).append(new_rel)
                        count += 1
        return count

    def get_subgraph(self, entity_ids: Set[str], depth: int = 1) -> Dict[str, Any]:
        entities = {}
        relations = []
        expanded = set(entity_ids)
        for _ in range(depth):
            new_ids = set()
            for eid in list(expanded):
                for rel in self._relations.get(eid, []):
                    new_ids.add(rel.target_id)
                for rel in self._incoming.get(eid, []):
                    new_ids.add(rel.source_id)
            expanded |= new_ids

        for eid in expanded:
            entity = self._entities.get(eid)
            if entity:
                entities[eid] = entity.to_dict()
            for rel in self._relations.get(eid, []):
                if rel.target_id in expanded:
                    relations.append(rel.to_dict())

        return {"entities": entities, "relations": relations}

    def save(self, path: str = "") -> str:
        save_path = path or self._persistence_path
        if not save_path:
            save_path = "/tmp/knowledge_graph.json"
        data = {
            "entities": {eid: e.to_dict() for eid, e in self._entities.items()},
            "relations": {
                src: [r.to_dict() for r in rels]
                for src, rels in self._relations.items()
            },
            "incoming": {
                tgt: [r.to_dict() for r in rels]
                for tgt, rels in self._incoming.items()
            },
            "inference_count": self._inference_count,
            "timestamp": time.time(),
        }
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)
        return save_path

    def load(self, path: str = "") -> bool:
        load_path = path or self._persistence_path
        if not load_path or not os.path.exists(load_path):
            return False
        with open(load_path) as f:
            data = json.load(f)
        self._entities = {}
        self._relations = {}
        self._incoming = {}
        self._alias_index = {}
        self._type_index = defaultdict(set)

        for eid, e_data in data.get("entities", {}).items():
            entity_type = EntityType(e_data["entity_type"])
            unit = KnowledgeUnit(
                id=e_data["id"], name=e_data["name"],
                description=e_data.get("description", ""),
                entity_type=entity_type,
                properties=e_data.get("properties", {}),
                timestamp=e_data.get("timestamp", time.time()),
                confidence=e_data.get("confidence", 1.0),
                source=e_data.get("source", ""),
                aliases=e_data.get("aliases", []),
            )
            self.add_entity(unit)

        for src, rels in data.get("relations", {}).items():
            for r_data in rels:
                relation = KnowledgeRelation(
                    source_id=r_data["source_id"],
                    target_id=r_data["target_id"],
                    relation_type=RelationType(r_data["relation_type"]),
                    weight=r_data.get("weight", 1.0),
                    properties=r_data.get("properties", {}),
                    timestamp=r_data.get("timestamp", time.time()),
                )
                self._relations.setdefault(src, []).append(relation)
                self._incoming.setdefault(r_data["target_id"], []).append(relation)

        self._inference_count = data.get("inference_count", 0)
        return True

    def clear(self):
        self._entities.clear()
        self._relations.clear()
        self._incoming.clear()
        self._alias_index.clear()
        self._type_index.clear()
        self._inference_count = 0
