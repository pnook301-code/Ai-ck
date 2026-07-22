"""Entity and Relation Extractors — parse text into KnowledgeGraph units"""

import re
from typing import Dict, List, Tuple
from kernel.memory.types import (
    KnowledgeUnit, KnowledgeRelation, EntityType, RelationType,
)


class EntityExtractor:
    def __init__(self):
        self._patterns = {
            EntityType.EMAIL: re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            EntityType.URL: re.compile(r"https?://[^\s]+"),
            EntityType.IP: re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        }

    def extract_from_text(self, text: str,
                          source: str = "extraction") -> List[KnowledgeUnit]:
        units = []
        seen = set()

        for etype, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                value = match.group()
                if value not in seen:
                    seen.add(value)
                    unit = KnowledgeUnit(
                        name=value,
                        description=f"Extracted {etype.value}",
                        entity_type=etype,
                        source=source,
                        properties={"pattern": "regex", "original": value},
                        confidence=0.9,
                    )
                    units.append(unit)

        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            if '.py' in line or '.ts' in line or '.js' in line:
                name = line.split('/')[-1] if '/' in line else line
                if name not in seen:
                    seen.add(name)
                    units.append(KnowledgeUnit(
                        name=name, description="Referenced file",
                        entity_type=EntityType.CODE, source=source,
                        properties={"path": line}, confidence=0.7,
                    ))

            if line.startswith('-') or line.startswith('*'):
                concept = line.lstrip('-* ').split(':')[0].strip()
                if concept and concept not in seen and len(concept) > 3:
                    seen.add(concept)
                    units.append(KnowledgeUnit(
                        name=concept, description="Listed item",
                        entity_type=EntityType.CONCEPT, source=source,
                        properties={"context": text[:200]}, confidence=0.6,
                    ))

        return units


class RelationExtractor:
    def __init__(self):
        self._patterns: List[Tuple[re.Pattern, RelationType]] = [
            (re.compile(r'\b(\w+)\s+(?:depends on|depends_on)\s+(\w+)'), RelationType.DEPENDS_ON),
            (re.compile(r'\b(\w+)\s+(?:causes?|leads? to|triggers?)\s+(\w+)'), RelationType.CAUSES),
            (re.compile(r'\b(\w+)\s+(?:follows?|after|then)\s+(\w+)'), RelationType.FOLLOWS),
            (re.compile(r'\b(\w+)\s+(?:contains?|has|includes?)\s+(\w+)'), RelationType.CONTAINS),
            (re.compile(r'\b(\w+)\s+(?:part of|part_of|belongs? to)\s+(\w+)'), RelationType.PART_OF),
            (re.compile(r'\b(\w+)\s+(?:created? by|written by|authored? by)\s+(\w+)'), RelationType.CREATED_BY),
            (re.compile(r'\b(\w+)\s+(?:uses?|utilizes?)\s+(\w+)'), RelationType.USES),
            (re.compile(r'\b(\w+)\s+(?:references?|see also|refers? to)\s+(\w+)'), RelationType.REFERENCES),
            (re.compile(r'\b(\w+)\s+(?:derived from|based on|built on)\s+(\w+)'), RelationType.DERIVED_FROM),
            (re.compile(r'\b(\w+)\s+(?:implements?)\s+(\w+)'), RelationType.IMPLEMENTS),
            (re.compile(r'\b(\w+)\s+(?:generates?|produces?|creates?)\s+(\w+)'), RelationType.GENERATES),
        ]

    def extract_from_text(self, text: str,
                          source: str = "extraction",
                          existing_entities: Dict[str, str] = None) -> List[KnowledgeRelation]:
        relations = []
        seen_pairs = set()

        for pattern, rel_type in self._patterns:
            for match in pattern.finditer(text):
                src_name = match.group(1).lower()
                tgt_name = match.group(2).lower()
                pair = (src_name, tgt_name, rel_type.value)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                src_id = existing_entities.get(src_name) if existing_entities else None
                tgt_id = existing_entities.get(tgt_name) if existing_entities else None

                if src_id and tgt_id:
                    relations.append(KnowledgeRelation(
                        source_id=src_id, target_id=tgt_id,
                        relation_type=rel_type,
                        properties={"source": source, "extracted": True},
                        weight=0.8,
                    ))

        return relations

    def extract_from_entities(self, entities: List[KnowledgeUnit]) -> List[KnowledgeRelation]:
        relations = []

        for i, src in enumerate(entities):
            for j, tgt in enumerate(entities):
                if i >= j:
                    continue
                if src.entity_type == tgt.entity_type:
                    relations.append(KnowledgeRelation(
                        source_id=src.id, target_id=tgt.id,
                        relation_type=RelationType.RELATED_TO,
                        properties={"inferred": True, "same_type": src.entity_type.value},
                        weight=0.5,
                    ))
        return relations
