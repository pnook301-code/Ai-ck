"""Memory OS types"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import time
import uuid


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class MemoryPriority(Enum):
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    CRITICAL = 1.0


@dataclass
class MemoryUnit:
    id: str = field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    content: str = ""
    embedding: List[float] = field(default_factory=list)
    memory_type: MemoryType = MemoryType.EPISODIC
    priority: MemoryPriority = MemoryPriority.MEDIUM
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self):
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "content": self.content,
            "memory_type": self.memory_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "tags": self.tags, "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class MemoryQuery:
    query: str = ""
    embedding: List[float] = field(default_factory=list)
    memory_type: Optional[MemoryType] = None
    tags: List[str] = field(default_factory=list)
    top_k: int = 10
    min_score: float = 0.0


@dataclass
class MemoryStats:
    total_units: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    total_queries: int = 0
    avg_query_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    vector_dim: int = 0


@dataclass
class MemoryLink:
    source_id: str = ""
    target_id: str = ""
    relation: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
