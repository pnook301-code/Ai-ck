"""Vector store for semantic memory — embeddings + cosine similarity search"""

from typing import List, Optional
import hashlib
import numpy as np
from .types import MemoryUnit, MemoryType


def _hash_tokenize(text: str, dim: int = 128) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


class VectorStore:
    def __init__(self, dim: int = 128):
        self.dim = dim
        self._vectors: dict[str, np.ndarray] = {}
        self._units: dict[str, MemoryUnit] = {}

    @property
    def size(self) -> int:
        return len(self._units)

    def insert(self, unit: MemoryUnit):
        if not unit.embedding:
            unit.embedding = _hash_tokenize(unit.content, self.dim).tolist()
        self._vectors[unit.id] = np.array(unit.embedding, dtype=np.float32)
        self._units[unit.id] = unit

    def delete(self, unit_id: str) -> bool:
        self._vectors.pop(unit_id, None)
        return self._units.pop(unit_id, None) is not None

    def update(self, unit: MemoryUnit):
        self.delete(unit.id)
        self.insert(unit)

    def get(self, unit_id: str) -> MemoryUnit:
        return self._units.get(unit_id)

    def search(self, query: str, top_k: int = 10, min_score: float = 0.0,
               memory_type: Optional[MemoryType] = None) -> List[tuple[MemoryUnit, float]]:
        if not self._vectors:
            return []
        qv = _hash_tokenize(query, self.dim)
        scores = []
        for uid, vec in self._vectors.items():
            unit = self._units[uid]
            if memory_type and unit.memory_type != memory_type:
                continue
            sim = float(np.dot(qv, vec))
            if sim >= min_score:
                scores.append((unit, sim))
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def search_by_vector(self, embedding: List[float], top_k: int = 10,
                         min_score: float = 0.0) -> List[tuple[MemoryUnit, float]]:
        if not self._vectors:
            return []
        qv = np.array(embedding, dtype=np.float32)
        scores = []
        for uid, vec in self._vectors.items():
            sim = float(np.dot(qv, vec))
            if sim >= min_score:
                scores.append((self._units[uid], sim))
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def clear(self):
        self._vectors.clear()
        self._units.clear()
