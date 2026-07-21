"""Memory OS types — extended with Knowledge Graph ontology"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
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


class EntityType(Enum):
    AGENT = "agent"
    CONCEPT = "concept"
    DOCUMENT = "document"
    TASK = "task"
    EVENT = "event"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CODE = "code"
    MEMORY = "memory"
    FUNCTION = "function"
    KNOWLEDGE = "knowledge"
    EMAIL = "email"
    URL = "url"
    IP = "ip"


class RelationType(Enum):
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    CAUSES = "causes"
    FOLLOWS = "follows"
    CONTAINS = "contains"
    PART_OF = "part_of"
    CREATED_BY = "created_by"
    USES = "uses"
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"
    CONFLICTS_WITH = "conflicts_with"
    IMPLEMENTS = "implements"
    GENERATES = "generates"


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


@dataclass
class KnowledgeUnit:
    id: str = field(default_factory=lambda: f"kg_{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    source: str = ""
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "entity_type": self.entity_type.value, "properties": self.properties,
            "timestamp": self.timestamp, "confidence": self.confidence,
            "source": self.source, "aliases": self.aliases,
        }


@dataclass
class KnowledgeRelation:
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id, "target_id": self.target_id,
            "relation_type": self.relation_type.value, "weight": self.weight,
            "properties": self.properties, "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeGraphStats:
    total_entities: int = 0
    total_relations: int = 0
    by_entity_type: Dict[str, int] = field(default_factory=dict)
    by_relation_type: Dict[str, int] = field(default_factory=dict)
    total_inferences: int = 0


@dataclass
class InferenceRule:
    name: str = ""
    antecedent: List[str] = field(default_factory=list)
    consequent: str = ""
    confidence: float = 1.0
