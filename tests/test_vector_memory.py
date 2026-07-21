"""Unit tests สำหรับ Vector Memory"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_memory import VectorMemory
from core.embedding import get_embedding, EMBEDDING_DIM


def test_vector_memory():
    vm = VectorMemory(collection_name="test", persist_dir="/tmp/test_chroma")
    vm.clear()
    vm.add_document("Apple is a fruit", {"category": "food"})
    vm.add_document("Tesla is a car", {"category": "auto"})
    vm.add_document("Python is a programming language", {"category": "tech"})
    results = vm.search("fruit", top_k=2)
    assert len(results) > 0
    results = vm.search("car", top_k=2, filter_metadata={"category": "food"})
    results = [r for r in results if (1 - r.get("distance", 1)) > 0.1]
    assert len(results) == 0
    stats = vm.get_stats()
    assert stats['count'] == 3
    print("✅ test_vector_memory passed")


def test_embedding():
    vec = get_embedding("hello world")
    assert len(vec) == EMBEDDING_DIM
    assert abs(sum(vec)) > 0
    sim = sum(a * b for a, b in zip(vec, vec))
    assert abs(sim - 1.0) < 0.01
    print("✅ test_embedding passed")


if __name__ == "__main__":
    test_embedding()
    test_vector_memory()
    print("🎉 All tests passed!")
