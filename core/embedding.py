"""Embedding Engine — hash-based (no external deps required for basic ops)"""

import hashlib
import numpy as np

EMBEDDING_DIM = 128


def get_embedding(text: str) -> list:
    vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % EMBEDDING_DIM
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


def get_embeddings_batch(texts: list) -> list:
    return [get_embedding(t) for t in texts]


def cosine_similarity(vec_a, vec_b):
    return float(np.dot(vec_a, vec_b))
