"""Knowledge Schema — ontology definitions and validation"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from kernel.memory.types import EntityType, RelationType


@dataclass
class EntitySchema:
    entity_type: EntityType
    required_properties: List[str] = field(default_factory=list)
    optional_properties: List[str] = field(default_factory=list)
    valid_relations: List[RelationType] = field(default_factory=list)
    description: str = ""
    aliases: List[str] = field(default_factory=list)

    def validate(self, properties: Dict[str, Any]) -> List[str]:
        errors = []
        for prop in self.required_properties:
            if prop not in properties:
                errors.append(f"Missing required property: {prop}")
        return errors


@dataclass
class RelationSchema:
    relation_type: RelationType
    source_types: List[EntityType] = field(default_factory=list)
    target_types: List[EntityType] = field(default_factory=list)
    description: str = ""
    bidirectional: bool = False

    def validate(self, source_type: EntityType, target_type: EntityType) -> List[str]:
        errors = []
        if self.source_types and source_type not in self.source_types:
            errors.append(f"Source type {source_type.value} not allowed for {self.relation_type.value}")
        if self.target_types and target_type not in self.target_types:
            errors.append(f"Target type {target_type.value} not allowed for {self.relation_type.value}")
        return errors


class KnowledgeSchema:
    def __init__(self):
        self._entities: Dict[EntityType, EntitySchema] = {}
        self._relations: Dict[RelationType, RelationSchema] = {}
        self._register_default_schemas()

    def _register_default_schemas(self):
        self.register_entity(EntitySchema(
            EntityType.AGENT,
            required_properties=["role", "capabilities"],
            optional_properties=["version", "model", "status"],
            valid_relations=[
                RelationType.CREATED_BY, RelationType.USES,
                RelationType.GENERATES, RelationType.RELATED_TO,
                RelationType.DEPENDS_ON,
            ],
            description="An AI agent with specific capabilities",
        ))
        self.register_entity(EntitySchema(
            EntityType.CONCEPT,
            required_properties=["definition"],
            optional_properties=["domain", "keywords", "references"],
            valid_relations=[
                RelationType.RELATED_TO, RelationType.PART_OF,
                RelationType.DERIVED_FROM, RelationType.IMPLEMENTS,
            ],
            description="An abstract concept or idea",
        ))
        self.register_entity(EntitySchema(
            EntityType.DOCUMENT,
            required_properties=["title"],
            optional_properties=["author", "created", "type", "summary"],
            valid_relations=[
                RelationType.CONTAINS, RelationType.REFERENCES,
                RelationType.DERIVED_FROM, RelationType.PART_OF,
            ],
            description="A document, file, or knowledge artifact",
        ))
        self.register_entity(EntitySchema(
            EntityType.TASK,
            required_properties=["description", "status"],
            optional_properties=["priority", "assignee", "deadline"],
            valid_relations=[
                RelationType.DEPENDS_ON, RelationType.CAUSES,
                RelationType.FOLLOWS, RelationType.PART_OF,
            ],
            description="A unit of work or objective",
        ))
        self.register_entity(EntitySchema(
            EntityType.EVENT,
            required_properties=["action", "timestamp"],
            optional_properties=["actor", "target", "outcome"],
            valid_relations=[
                RelationType.CAUSES, RelationType.FOLLOWS,
                RelationType.GENERATES, RelationType.REFERENCES,
            ],
            description="An occurrence or state change",
        ))
        self.register_entity(EntitySchema(
            EntityType.CODE,
            required_properties=["language", "purpose"],
            optional_properties=["module", "dependencies", "version"],
            valid_relations=[
                RelationType.IMPLEMENTS, RelationType.USES,
                RelationType.DEPENDS_ON, RelationType.REFERENCES,
                RelationType.PART_OF,
            ],
            description="A code module, function, or component",
        ))

    def register_entity(self, schema: EntitySchema):
        self._entities[schema.entity_type] = schema

    def register_relation(self, schema: RelationSchema):
        self._relations[schema.relation_type] = schema

    def get_entity_schema(self, entity_type: EntityType) -> Optional[EntitySchema]:
        return self._entities.get(entity_type)

    def get_relation_schema(self, relation_type: RelationType) -> Optional[RelationSchema]:
        return self._relations.get(relation_type)

    def validate_entity(self, entity_type: EntityType,
                        properties: Dict[str, Any]) -> List[str]:
        schema = self._entities.get(entity_type)
        if not schema:
            return [f"No schema defined for {entity_type.value}"]
        return schema.validate(properties)

    def validate_relation(self, relation_type: RelationType,
                          source_type: EntityType,
                          target_type: EntityType) -> List[str]:
        schema = self._relations.get(relation_type)
        if not schema:
            return []
        return schema.validate(source_type, target_type)

    def get_valid_relations(self, entity_type: EntityType) -> List[RelationType]:
        schema = self._entities.get(entity_type)
        return schema.valid_relations if schema else list(RelationType)
