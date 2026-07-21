"""Vector Memory — numpy-based vector store with cosine similarity search"""
import numpy as np
import os
import uuid
from typing import List, Dict, Optional
from .embedding import get_embedding, EMBEDDING_DIM


class VectorMemory:
    def __init__(self, collection_name: str = "ck_nexus", persist_dir: str = "./chroma_db"):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._docs: Dict[str, dict] = {}

    def add_document(self, content: str, metadata: Optional[Dict] = None,
                     doc_id: Optional[str] = None) -> str:
        if metadata is None:
            metadata = {}
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        embedding = get_embedding(content)
        self._docs[doc_id] = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata,
        }
        return doc_id

    def search(self, query: str, top_k: int = 5,
               filter_metadata: Optional[Dict] = None) -> List[Dict]:
        if not self._docs:
            return []
        qv = get_embedding(query)
        scored = []
        for doc_id, doc in self._docs.items():
            if filter_metadata:
                match = all(doc["metadata"].get(k) == v for k, v in filter_metadata.items())
                if not match:
                    continue
            sim = float(np.dot(qv, doc["embedding"]))
            scored.append((doc_id, doc["content"], doc["metadata"], sim))
        scored.sort(key=lambda x: -x[3])
        return [
            {"id": sid, "content": c, "metadata": m, "distance": 1 - s}
            for sid, c, m, s in scored[:top_k]
        ]

    def delete(self, doc_ids: List[str]):
        for did in doc_ids:
            self._docs.pop(did, None)

    def get_stats(self) -> Dict:
        return {
            "collection": self.collection_name,
            "count": len(self._docs),
            "persist_dir": self.persist_dir,
            "embedding_dim": EMBEDDING_DIM,
        }

    def clear(self):
        self._docs.clear()


_vector_memory = None


def get_vector_memory() -> VectorMemory:
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
    return _vector_memory
