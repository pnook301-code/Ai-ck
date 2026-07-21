"""Graph store for relational memory — entity-links with weighted traversal"""

from typing import Any, Dict, List, Optional
from .types import MemoryUnit, MemoryLink


class GraphStore:
    def __init__(self):
        self._nodes: Dict[str, MemoryUnit] = {}
        self._edges: Dict[str, List[MemoryLink]] = {}
        self._incoming: Dict[str, List[MemoryLink]] = {}

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._edges.values())

    def add_node(self, unit: MemoryUnit):
        self._nodes[unit.id] = unit

    def get_node(self, node_id: str) -> Optional[MemoryUnit]:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str):
        self._nodes.pop(node_id, None)
        self._edges.pop(node_id, None)
        self._incoming.pop(node_id, None)
        for edges in self._edges.values():
            edges[:] = [e for e in edges if e.target_id != node_id]
        for edges in self._incoming.values():
            edges[:] = [e for e in edges if e.source_id != node_id]

    def add_edge(self, link: MemoryLink):
        self._edges.setdefault(link.source_id, []).append(link)
        self._incoming.setdefault(link.target_id, []).append(link)

    def get_outgoing(self, node_id: str) -> List[MemoryLink]:
        return self._edges.get(node_id, [])

    def get_incoming(self, node_id: str) -> List[MemoryLink]:
        return self._incoming.get(node_id, [])

    def traverse(self, start_id: str, relation: Optional[str] = None,
                 max_depth: int = 2) -> List[tuple[MemoryUnit, str, float]]:
        results = []
        visited = {start_id}
        queue = [(start_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for link in self._edges.get(current, []):
                if relation and link.relation != relation:
                    continue
                if link.target_id not in visited:
                    visited.add(link.target_id)
                    target = self._nodes.get(link.target_id)
                    if target:
                        results.append((target, link.relation, link.weight))
                    queue.append((link.target_id, depth + 1))
        return results

    def find_path(self, from_id: str, to_id: str, max_depth: int = 5) -> List[List[MemoryLink]]:
        paths = []
        def _dfs(current, target, path, visited):
            if len(path) > max_depth:
                return
            if current == target:
                paths.append(list(path))
                return
            for link in self._edges.get(current, []):
                if link.target_id not in visited:
                    visited.add(link.target_id)
                    path.append(link)
                    _dfs(link.target_id, target, path, visited)
                    path.pop()
                    visited.discard(link.target_id)
        _dfs(from_id, to_id, [], {from_id})
        return paths

    def query_by_relation(self, relation: str) -> List[tuple[MemoryUnit, MemoryUnit]]:
        pairs = []
        for src_id, edges in self._edges.items():
            src = self._nodes.get(src_id)
            if not src:
                continue
            for link in edges:
                if link.relation == relation:
                    tgt = self._nodes.get(link.target_id)
                    if tgt:
                        pairs.append((src, tgt))
        return pairs

    def clear(self):
        self._nodes.clear()
        self._edges.clear()
        self._incoming.clear()
