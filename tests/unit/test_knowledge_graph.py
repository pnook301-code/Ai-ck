"""Tests for Knowledge Graph"""

import pytest
import tempfile
import os
import json
from kernel.memory import KnowledgeGraph
from kernel.memory.types import (
    KnowledgeUnit, KnowledgeRelation, EntityType, RelationType,
)


@pytest.fixture
def kg():
    return KnowledgeGraph()


class TestKnowledgeGraph:
    def test_add_and_get_entity(self, kg):
        unit = KnowledgeUnit(
            name="test_agent", description="A test agent",
            entity_type=EntityType.AGENT,
            properties={"role": "tester"},
            aliases=["tester", "qa"],
        )
        eid = kg.add_entity(unit)
        assert eid == unit.id
        retrieved = kg.get_entity(eid)
        assert retrieved is not None
        assert retrieved.name == "test_agent"
        assert retrieved.entity_type == EntityType.AGENT

    def test_find_by_name(self, kg):
        kg.add_entity(KnowledgeUnit(name="RedisDB", description="A cache", entity_type=EntityType.CONCEPT))
        found = kg.find_by_name("redisdb")
        assert found is not None
        assert found.name == "RedisDB"

    def test_find_by_alias(self, kg):
        kg.add_entity(KnowledgeUnit(name="CK-NEXUS", description="AIOS", entity_type=EntityType.CONCEPT, aliases=["nexus", "core"]))
        found = kg.find_by_name("nexus")
        assert found is not None
        assert found.name == "CK-NEXUS"

    def test_find_by_type(self, kg):
        for i in range(3):
            kg.add_entity(KnowledgeUnit(name=f"agent_{i}", entity_type=EntityType.AGENT))
        for i in range(2):
            kg.add_entity(KnowledgeUnit(name=f"doc_{i}", entity_type=EntityType.DOCUMENT))
        agents = kg.find_by_type(EntityType.AGENT)
        docs = kg.find_by_type(EntityType.DOCUMENT)
        assert len(agents) == 3
        assert len(docs) == 2

    def test_add_relation(self, kg):
        src = KnowledgeUnit(name="source", entity_type=EntityType.CONCEPT)
        tgt = KnowledgeUnit(name="target", entity_type=EntityType.CONCEPT)
        kg.add_entity(src)
        kg.add_entity(tgt)
        rel = KnowledgeRelation(
            source_id=src.id, target_id=tgt.id,
            relation_type=RelationType.DEPENDS_ON,
            weight=0.9,
        )
        assert kg.add_relation(rel) is True
        outgoing = kg.get_relations(src.id)
        assert len(outgoing) == 1
        assert outgoing[0].relation_type == RelationType.DEPENDS_ON

    def test_add_relation_fails_missing_source(self, kg):
        tgt = KnowledgeUnit(name="target", entity_type=EntityType.CONCEPT)
        kg.add_entity(tgt)
        rel = KnowledgeRelation(
            source_id="nonexistent", target_id=tgt.id,
            relation_type=RelationType.RELATED_TO,
        )
        assert kg.add_relation(rel) is False

    def test_remove_entity(self, kg):
        unit = KnowledgeUnit(name="delete_me", entity_type=EntityType.CONCEPT)
        eid = kg.add_entity(unit)
        assert kg.get_entity(eid) is not None
        assert kg.remove_entity(eid) is True
        assert kg.get_entity(eid) is None

    def test_traverse(self, kg):
        a = KnowledgeUnit(name="A", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="B", entity_type=EntityType.CONCEPT)
        c = KnowledgeUnit(name="C", entity_type=EntityType.CONCEPT)
        for e in [a, b, c]:
            kg.add_entity(e)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.DEPENDS_ON))
        kg.add_relation(KnowledgeRelation(b.id, c.id, RelationType.DEPENDS_ON))
        results = kg.traverse(a.id, max_depth=2)
        names = {r[0].name for r in results}
        assert "B" in names
        assert "C" in names

    def test_find_path(self, kg):
        a = KnowledgeUnit(name="A", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="B", entity_type=EntityType.CONCEPT)
        c = KnowledgeUnit(name="C", entity_type=EntityType.CONCEPT)
        for e in [a, b, c]:
            kg.add_entity(e)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.RELATED_TO))
        kg.add_relation(KnowledgeRelation(b.id, c.id, RelationType.RELATED_TO))
        paths = kg.find_path(a.id, c.id)
        assert len(paths) == 1
        assert len(paths[0]) == 2

    def test_query(self, kg):
        agent = KnowledgeUnit(name="dev_agent", entity_type=EntityType.AGENT)
        code = KnowledgeUnit(name="module.py", entity_type=EntityType.CODE)
        kg.add_entity(agent)
        kg.add_entity(code)
        kg.add_relation(KnowledgeRelation(agent.id, code.id, RelationType.GENERATES))
        results = kg.query(source_type=EntityType.AGENT, target_type=EntityType.CODE)
        assert len(results) == 1
        assert results[0][0].name == "dev_agent"
        assert results[0][2].name == "module.py"

    def test_inference(self, kg):
        a = KnowledgeUnit(name="A", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="B", entity_type=EntityType.CONCEPT)
        c = KnowledgeUnit(name="C", entity_type=EntityType.CONCEPT)
        for e in [a, b, c]:
            kg.add_entity(e)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.DEPENDS_ON))
        kg.add_relation(KnowledgeRelation(b.id, c.id, RelationType.DEPENDS_ON))
        count = kg.infer()
        assert count > 0
        assert kg.stats.total_inferences > 0
        indirect = kg.get_relations(a.id)
        rel_types = {r.relation_type for r in indirect}
        assert len(indirect) > 1

    def test_save_and_load(self, kg, temp_dir):
        for i in range(3):
            kg.add_entity(KnowledgeUnit(name=f"entity_{i}", entity_type=EntityType.CONCEPT))
        save_path = os.path.join(temp_dir, "kg_test.json")
        path = kg.save(save_path)
        assert os.path.exists(path)

        kg2 = KnowledgeGraph()
        assert kg2.load(save_path) is True
        assert kg2.stats.total_entities == 3

    def test_clear(self, kg):
        kg.add_entity(KnowledgeUnit(name="temp", entity_type=EntityType.CONCEPT))
        assert kg.stats.total_entities == 1
        kg.clear()
        assert kg.stats.total_entities == 0

    def test_get_subgraph(self, kg):
        a = KnowledgeUnit(name="center", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="neighbor", entity_type=EntityType.CONCEPT)
        kg.add_entity(a)
        kg.add_entity(b)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.RELATED_TO))
        sub = kg.get_subgraph({a.id})
        assert len(sub["entities"]) == 2
        assert len(sub["relations"]) == 1

    def test_stats(self, kg):
        kg.add_entity(KnowledgeUnit(name="stats_test", entity_type=EntityType.AGENT))
        kg.add_entity(KnowledgeUnit(name="stats_concept", entity_type=EntityType.CONCEPT))
        kg.add_entity(KnowledgeUnit(name="stats_code", entity_type=EntityType.CODE))
        stats = kg.stats
        assert stats.total_entities == 3
        assert stats.by_entity_type.get("agent") == 1
        assert stats.by_entity_type.get("concept") == 1
        assert stats.by_entity_type.get("code") == 1
