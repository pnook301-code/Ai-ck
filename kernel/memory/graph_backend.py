"""Abstract graph backend interface + JSON + Neo4j implementations."""
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from collections import deque


class GraphBackend(ABC):
    @abstractmethod
    def add_entity(self, entity_id: str, name: str, entity_type: str, description: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: ...

    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_entities(self, entity_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def delete_entity(self, entity_id: str) -> bool: ...

    @abstractmethod
    def add_relation(self, source_id: str, target_id: str, relation_type: str, weight: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: ...

    @abstractmethod
    def get_relations(self, entity_id: str, direction: str = "both") -> List[Dict[str, Any]]: ...

    @abstractmethod
    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> Optional[List[str]]: ...

    @abstractmethod
    def bfs(self, start_id: str, max_depth: int = 3) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]: ...

    @abstractmethod
    def clear(self): ...


class JSONGraphBackend(GraphBackend):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relations: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath) as f:
                data = json.load(f)
            self._entities = data.get("entities", {})
            self._relations = data.get("relations", {})

    def _save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump({"entities": self._entities, "relations": self._relations}, f, indent=2)

    def add_entity(self, entity_id, name, entity_type, description="", metadata=None):
        entity = {"id": entity_id, "name": name, "type": entity_type, "description": description, "metadata": metadata or {}, "created_at": time.time()}
        self._entities[entity_id] = entity
        self._save()
        return entity

    def get_entity(self, entity_id):
        return self._entities.get(entity_id)

    def list_entities(self, entity_type=None, limit=100):
        entities = list(self._entities.values())
        if entity_type:
            entities = [e for e in entities if e.get("type") == entity_type]
        return entities[:limit]

    def delete_entity(self, entity_id):
        if entity_id in self._entities:
            del self._entities[entity_id]
            self._relations = {k: v for k, v in self._relations.items() if v.get("source") != entity_id and v.get("target") != entity_id}
            self._save()
            return True
        return False

    def add_relation(self, source_id, target_id, relation_type, weight=1.0, metadata=None):
        rid = f"rel_{source_id}_{target_id}_{relation_type}"
        relation = {"id": rid, "source": source_id, "target": target_id, "type": relation_type, "weight": weight, "metadata": metadata or {}, "created_at": time.time()}
        self._relations[rid] = relation
        self._save()
        return relation

    def get_relations(self, entity_id, direction="both"):
        results = []
        for r in self._relations.values():
            if direction == "outgoing" and r.get("source") == entity_id:
                results.append(r)
            elif direction == "incoming" and r.get("target") == entity_id:
                results.append(r)
            elif direction == "both" and (r.get("source") == entity_id or r.get("target") == entity_id):
                results.append(r)
        return results

    def find_path(self, source_id, target_id, max_depth=5):
        if source_id == target_id:
            return [source_id]
        visited = {source_id}
        queue = deque([(source_id, [source_id])])
        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for r in self.get_relations(current, "outgoing"):
                neighbor = r["target"]
                if neighbor == target_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def bfs(self, start_id, max_depth=3):
        visited = {start_id: 0}
        queue = deque([start_id])
        results = []
        while queue:
            node = queue.popleft()
            depth = visited[node]
            entity = self.get_entity(node)
            if entity:
                results.append({"entity": entity, "depth": depth})
            if depth < max_depth:
                for r in self.get_relations(node, "outgoing"):
                    neighbor = r["target"]
                    if neighbor not in visited:
                        visited[neighbor] = depth + 1
                        queue.append(neighbor)
        return results

    def get_stats(self):
        types = {}
        for e in self._entities.values():
            t = e.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        return {"entities": len(self._entities), "relations": len(self._relations), "entity_types": types}

    def clear(self):
        self._entities.clear()
        self._relations.clear()
        self._save()


class Neo4jGraphBackend(GraphBackend):
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = ""):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
        except ImportError:
            raise ImportError("pip install neo4j")
        except Exception:
            self._driver = None

    def _run(self, query, parameters=None):
        if not self._driver:
            return []
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(r) for r in result]

    def add_entity(self, entity_id, name, entity_type, description="", metadata=None):
        query = "MERGE (e:Entity {id: $id}) SET e.name = $name, e.type = $type, e.desc = $desc, e.meta = $meta, e.created = $created RETURN e"
        params = {"id": entity_id, "name": name, "type": entity_type, "desc": description, "meta": json.dumps(metadata or {}), "created": time.time()}
        self._run(query, params)
        return {"id": entity_id, "name": name, "type": entity_type, "description": description, "metadata": metadata or {}}

    def get_entity(self, entity_id):
        results = self._run("MATCH (e:Entity {id: $id}) RETURN e", {"id": entity_id})
        return results[0]["e"] if results else None

    def list_entities(self, entity_type=None, limit=100):
        if entity_type:
            return self._run("MATCH (e:Entity {type: $type}) RETURN e LIMIT $limit", {"type": entity_type, "limit": limit})
        return self._run("MATCH (e:Entity) RETURN e LIMIT $limit", {"limit": limit})

    def delete_entity(self, entity_id):
        self._run("MATCH (e:Entity {id: $id}) DETACH DELETE e", {"id": entity_id})
        return True

    def add_relation(self, source_id, target_id, relation_type, weight=1.0, metadata=None):
        query = f"MATCH (a:Entity {{id: $src}}), (b:Entity {{id: $tgt}}) MERGE (a)-[r:{relation_type}]->(b) SET r.weight = $w RETURN type(r)"
        self._run(query, {"src": source_id, "tgt": target_id, "w": weight})
        return {"source": source_id, "target": target_id, "type": relation_type, "weight": weight}

    def get_relations(self, entity_id, direction="both"):
        if direction == "outgoing":
            return self._run("MATCH (e:Entity {id: $id})-[r]->(n) RETURN r, n.id as target", {"id": entity_id})
        elif direction == "incoming":
            return self._run("MATCH (e:Entity {id: $id})<-[r]-(n) RETURN r, n.id as source", {"id": entity_id})
        return self._run("MATCH (e:Entity {id: $id})-[r]-(n) RETURN r, n.id as other", {"id": entity_id})

    def find_path(self, source_id, target_id, max_depth=5):
        query = f"MATCH path = shortestPath((a:Entity {{id: $src}})-[*..{max_depth}]-(b:Entity {{id: $tgt}})) RETURN [n IN nodes(path) | n.id] as path"
        results = self._run(query, {"src": source_id, "tgt": target_id})
        return results[0]["path"] if results else None

    def bfs(self, start_id, max_depth=3):
        query = f"MATCH (start:Entity {{id: $id}}), (start)-[*0..{max_depth}]-(n:Entity) RETURN DISTINCT n, 0 as depth LIMIT 100"
        return self._run(query, {"id": start_id})

    def get_stats(self):
        entities = self._run("MATCH (e:Entity) RETURN count(e) as count")
        relations = self._run("MATCH ()-[r]->() RETURN count(r) as count")
        types = self._run("MATCH (e:Entity) RETURN e.type as type, count(e) as count")
        return {"entities": entities[0]["count"] if entities else 0, "relations": relations[0]["count"] if relations else 0, "entity_types": {t["type"]: t["count"] for t in types}}

    def clear(self):
        self._run("MATCH (n) DETACH DELETE n")


def create_backend(backend_type: str = "auto", **kwargs) -> GraphBackend:
    if backend_type == "neo4j":
        return Neo4jGraphBackend(**kwargs)
    elif backend_type == "json":
        return JSONGraphBackend(filepath=kwargs.get("filepath", "knowledge/graph.json"))
    else:
        try:
            backend = Neo4jGraphBackend(**kwargs)
            if backend._driver:
                return backend
        except Exception:
            pass
        return JSONGraphBackend(filepath=kwargs.get("filepath", os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge", "global_ai_research.json")))
