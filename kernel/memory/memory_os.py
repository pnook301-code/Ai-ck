"""Unified Memory OS — hybrid vector + graph + semantic recall"""

import time
from typing import Any, Dict, List, Optional
from .types import (
    MemoryUnit, MemoryStats, MemoryLink,
    MemoryType, MemoryPriority,
)
from .vector_store import VectorStore
from .graph_store import GraphStore


class MemoryOS:
    def __init__(self):
        self.vector = VectorStore(dim=128)
        self.graph = GraphStore()
        self._query_count = 0
        self._query_time_total = 0.0
        self._cache: Dict[str, List[tuple[MemoryUnit, float]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def stats(self) -> MemoryStats:
        by_type = {}
        for unit in self.vector._units.values():
            t = unit.memory_type.value
            by_type[t] = by_type.get(t, 0) + 1
        avg_ms = (self._query_time_total / self._query_count * 1000
                  if self._query_count > 0 else 0)
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return MemoryStats(
            total_units=self.vector.size,
            by_type=by_type,
            total_queries=self._query_count,
            avg_query_time_ms=avg_ms,
            cache_hit_rate=hit_rate,
            vector_dim=self.vector.dim,
        )

    def remember(self, content: str, memory_type: MemoryType = MemoryType.EPISODIC,
                 priority: MemoryPriority = MemoryPriority.MEDIUM,
                 tags: List[str] = None, source: str = "",
                 metadata: Dict[str, Any] = None) -> MemoryUnit:
        unit = MemoryUnit(
            content=content,
            memory_type=memory_type,
            priority=priority,
            tags=tags or [],
            source=source,
            metadata=metadata or {},
        )
        self.vector.insert(unit)
        self.graph.add_node(unit)
        self._cache.clear()
        return unit

    def recall(self, query: str, top_k: int = 10,
               memory_type: Optional[MemoryType] = None,
               min_score: float = 0.0) -> List[MemoryUnit]:
        start = time.time()
        cache_key = f"{query}:{top_k}:{memory_type}:{min_score}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._cache_hits += 1
            self._query_count += 1
            self._query_time_total += time.time() - start
            return [unit for unit, _ in cached]

        self._cache_misses += 1
        results = self.vector.search(query, top_k, min_score, memory_type)
        units = []
        for unit, score in results:
            unit.touch()
            if score >= min_score:
                units.append(unit)
        self._cache[cache_key] = [(u, 0) for u in units]
        self._query_count += 1
        self._query_time_total += time.time() - start
        return units

    def recall_by_tags(self, tags: List[str], memory_type: Optional[MemoryType] = None,
                       top_k: int = 20) -> List[MemoryUnit]:
        results = []
        for unit in self.vector._units.values():
            if memory_type and unit.memory_type != memory_type:
                continue
            if any(t in unit.tags for t in tags):
                results.append(unit)
        results.sort(key=lambda u: -u.priority.value)
        return results[:top_k]

    def recall_related(self, unit_id: str, relation: Optional[str] = None,
                       max_depth: int = 2) -> List[MemoryUnit]:
        visited = {unit_id}
        related = []
        queue = [(unit_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for link in self.graph.get_outgoing(current):
                if relation and link.relation != relation:
                    continue
                if link.target_id not in visited:
                    visited.add(link.target_id)
                    node = self.graph.get_node(link.target_id)
                    if node:
                        related.append(node)
                    queue.append((link.target_id, depth + 1))
        return related

    def link(self, source_id: str, target_id: str, relation: str = "related",
             weight: float = 1.0, metadata: Dict[str, Any] = None) -> bool:
        src = self.graph.get_node(source_id)
        tgt = self.graph.get_node(target_id)
        if not src or not tgt:
            return False
        link = MemoryLink(
            source_id=source_id, target_id=target_id,
            relation=relation, weight=weight,
            metadata=metadata or {},
        )
        self.graph.add_edge(link)
        return True

    def forget(self, unit_id: str) -> bool:
        self.vector.delete(unit_id)
        self.graph.remove_node(unit_id)
        self._cache.clear()
        return True

    def get_unit(self, unit_id: str) -> Optional[MemoryUnit]:
        return self.vector.get(unit_id) or self.graph.get_node(unit_id)

    def clear(self):
        self.vector.clear()
        self.graph.clear()
        self._cache.clear()
        self._query_count = 0
        self._query_time_total = 0.0
        self._cache_hits = 0
        self._cache_misses = 0

    def to_dict(self) -> Dict[str, Any]:
        s = self.stats
        return {
            "stats": {
                "total_units": s.total_units,
                "by_type": s.by_type,
                "total_queries": s.total_queries,
                "avg_query_time_ms": round(s.avg_query_time_ms, 2),
                "cache_hit_rate": round(s.cache_hit_rate, 3),
                "vector_dim": s.vector_dim,
                "graph_nodes": self.graph.node_count,
                "graph_edges": self.graph.edge_count,
            },
        }
