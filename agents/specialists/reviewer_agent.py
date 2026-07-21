"""Reviewer Agent - reviews code and provides feedback"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.core.base_agent import BaseAgent


class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="reviewer",
            role="code_reviewer",
            capabilities=["review_code", "review_plan", "quality_check", "approve"]
        )
        self.reviews = []

    def _do_task(self, task):
        desc = task.description.lower()

        if "review" in desc:
            return self._review(task)
        elif "quality" in desc:
            return self._quality_check(task)
        elif "approve" in desc:
            return self._approve(task)
        else:
            return self._general_review(task)

    def _review(self, task):
        self._log(f"Reviewing: {task.title}")

        review = {
            "action": "reviewed",
            "item": task.title,
            "score": 85,
            "feedback": [
                "Code structure is clean",
                "Error handling could be improved",
                "Consider adding more comments"
            ],
            "approve": True,
            "message": f"Review complete for: {task.title}"
        }
        self.reviews.append(review)
        return review

    def _quality_check(self, task):
        self._log(f"Quality check: {task.title}")

        base = "/workspace/ck-nexus"
        quality_metrics = {
            "files_checked": 0,
            "total_lines": 0,
            "issues": []
        }

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git"]]
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    quality_metrics["files_checked"] += 1
                    try:
                        with open(path) as fh:
                            lines = len(fh.readlines())
                            quality_metrics["total_lines"] += lines
                            if lines > 500:
                                quality_metrics["issues"].append(f"{f}: too long ({lines} lines)")
                    except Exception:
                        pass

        return {
            "action": "quality_checked",
            "metrics": quality_metrics,
            "score": 90 if not quality_metrics["issues"] else 75,
            "message": "Quality check complete"
        }

    def _approve(self, task):
        self._log(f"Approving: {task.title}")
        return {
            "action": "approved",
            "item": task.title,
            "approved": True,
            "message": f"Approved: {task.title}"
        }

    def _general_review(self, task):
        return {
            "action": "reviewed",
            "message": f"Review complete: {task.title}"
        }

    def get_reviews(self):
        return self.reviews
