"""Feedback Loop — learns from user ratings to improve retrieval"""

import json
import os
import time

from core.vector_memory import get_vector_memory

FEEDBACK_DB = os.path.expanduser("~/.ck-nexus/feedback.json")

class FeedbackIntegration:
    def __init__(self):
        self.db_path = FEEDBACK_DB
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path) as f:
                self.data = json.load(f)
        else:
            self.data = {"feedbacks": [], "stats": {"total": 0, "avg": 0.0}}

    def _save(self):
        n = len(self.data["feedbacks"])
        self.data["stats"]["total"] = n
        self.data["stats"]["avg"] = (
            sum(f["relevance"] for f in self.data["feedbacks"]) / n if n > 0 else 0.0
        )
        with open(self.db_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def record(self, doc_id: str, relevance: float):
        self.data["feedbacks"].append({
            "doc_id": doc_id,
            "relevance": relevance,
            "timestamp": time.time(),
        })
        self._save()

    def get_stats(self):
        return self.data["stats"]

    def get_feedback_for_doc(self, doc_id: str):
        return [f for f in self.data["feedbacks"] if f["doc_id"] == doc_id]

    def adjust_importance(self, doc_id: str, base_importance: float = 0.5) -> float:
        fb = self.get_feedback_for_doc(doc_id)
        if not fb:
            return base_importance
        avg_rel = sum(f["relevance"] for f in fb) / len(fb)
        return base_importance * (0.5 + avg_rel)
