"""Tests for Memory OS"""

import pytest
from kernel.memory import MemoryOS, MemoryType, MemoryPriority, MemoryUnit, MemoryStats


@pytest.fixture
def mem():
    return MemoryOS()


class TestMemoryOS:
    def test_remember_and_recall(self, mem):
        unit = mem.remember("hello world", MemoryType.EPISODIC, tags=["greeting"])
        assert unit.id.startswith("mem_")
        assert mem.stats.total_units == 1
        results = mem.recall("hello", top_k=5)
        assert len(results) == 1
        assert results[0].content == "hello world"

    def test_recall_empty(self, mem):
        results = mem.recall("nothing", top_k=5)
        assert len(results) == 0

    def test_recall_by_type(self, mem):
        mem.remember("episodic event", MemoryType.EPISODIC)
        mem.remember("semantic fact", MemoryType.SEMANTIC)
        epi = mem.recall("event", memory_type=MemoryType.EPISODIC)
        sem = mem.recall("fact", memory_type=MemoryType.SEMANTIC)
        assert len(epi) == 1
        assert len(sem) == 1
        assert epi[0].content == "episodic event"
        assert sem[0].content == "semantic fact"

    def test_recall_by_tags(self, mem):
        mem.remember("secret", tags=["confidential", "high"])
        mem.remember("public", tags=["public", "low"])
        results = mem.recall_by_tags(["confidential"])
        assert len(results) == 1
        assert results[0].content == "secret"

    def test_link_and_related(self, mem):
        a = mem.remember("node A")
        b = mem.remember("node B")
        c = mem.remember("node C")
        assert mem.link(a.id, b.id, "connects")
        assert mem.link(b.id, c.id, "connects")
        related = mem.recall_related(a.id)
        assert len(related) >= 1

    def test_link_nonexistent(self, mem):
        assert not mem.link("nonexistent", "also_no", "test")

    def test_forget(self, mem):
        unit = mem.remember("to forget")
        assert mem.stats.total_units == 1
        mem.forget(unit.id)
        assert mem.stats.total_units == 0

    def test_get_unit(self, mem):
        unit = mem.remember("find me")
        found = mem.get_unit(unit.id)
        assert found is not None
        assert found.content == "find me"
        assert mem.get_unit("nonexistent") is None

    def test_clear(self, mem):
        mem.remember("a")
        mem.remember("b")
        mem.remember("c")
        assert mem.stats.total_units == 3
        mem.clear()
        assert mem.stats.total_units == 0

    def test_multiple_types(self, mem):
        for t in MemoryType:
            mem.remember(f"content for {t.value}", t)
        assert mem.stats.total_units == 4
        stats = mem.stats
        assert stats.by_type["episodic"] == 1
        assert stats.by_type["semantic"] == 1
        assert stats.by_type["procedural"] == 1
        assert stats.by_type["working"] == 1

    def test_priority_scoring(self, mem):
        low = mem.remember("low priority", priority=MemoryPriority.LOW)
        high = mem.remember("high priority", priority=MemoryPriority.HIGH)
        assert high.priority.value > low.priority.value

    def test_touch_updates_access(self, mem):
        unit = mem.remember("touching")
        count_before = unit.access_count
        mem.recall("touching")
        assert unit.access_count > count_before

    def test_recall_with_source(self, mem):
        mem.remember("user specific login data", source="user", tags=["user"])
        mem.remember("system configuration settings", source="system", tags=["system"])
        results = mem.recall_by_tags(["user"])
        assert len(results) == 1
        assert results[0].source == "user"

    def test_to_dict(self, mem):
        mem.remember("data")
        d = mem.to_dict()
        assert "stats" in d
        assert d["stats"]["total_units"] == 1


class TestGraphStore:
    def test_node_count(self, mem):
        assert mem.graph.node_count == 0
        mem.remember("a")
        assert mem.graph.node_count == 1

    def test_edge_count(self, mem):
        a = mem.remember("a")
        b = mem.remember("b")
        mem.link(a.id, b.id, "related")
        assert mem.graph.edge_count == 1

    def test_traverse(self, mem):
        a = mem.remember("a")
        b = mem.remember("b")
        c = mem.remember("c")
        mem.link(a.id, b.id, "knows")
        mem.link(b.id, c.id, "knows")
        related = mem.recall_related(a.id, max_depth=3)
        assert len(related) >= 2

    def test_path_finding(self, mem):
        a = mem.remember("a")
        b = mem.remember("b")
        c = mem.remember("c")
        mem.link(a.id, b.id, "to")
        mem.link(b.id, c.id, "to")
        paths = mem.graph.find_path(a.id, c.id)
        assert len(paths) >= 1


class TestMemoryUnit:
    def test_create(self):
        u = MemoryUnit(content="test")
        assert u.id.startswith("mem_")
        assert u.memory_type == MemoryType.EPISODIC
        assert u.priority == MemoryPriority.MEDIUM

    def test_to_dict(self):
        u = MemoryUnit(content="test", tags=["a", "b"], source="user")
        d = u.to_dict()
        assert d["content"] == "test"
        assert d["tags"] == ["a", "b"]
        assert d["source"] == "user"

    def test_touch(self):
        u = MemoryUnit()
        old_count = u.access_count
        u.touch()
        assert u.access_count == old_count + 1


class TestMemoryStats:
    def test_defaults(self):
        s = MemoryStats()
        assert s.total_units == 0
        assert s.total_queries == 0
        assert s.avg_query_time_ms == 0.0
