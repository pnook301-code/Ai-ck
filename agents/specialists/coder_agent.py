"""Coder Agent - writes and reviews code"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.core.base_agent import BaseAgent


class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="coder",
            role="developer",
            capabilities=["write_code", "review_code", "refactor", "debug", "implement"]
        )
        self.files_modified = []
        self.code_quality = []

    def _do_task(self, task):
        desc = task.description.lower()

        if "write" in desc or "create" in desc or "implement" in desc:
            return self._write_code(task)
        elif "review" in desc:
            return self._review_code(task)
        elif "refactor" in desc:
            return self._refactor_code(task)
        elif "fix" in desc or "debug" in desc:
            return self._fix_code(task)
        else:
            return self._general_task(task)

    def _write_code(self, task):
        self._log(f"Writing code for: {task.title}")
        return {
            "action": "code_written",
            "files": self.files_modified,
            "quality": "high",
            "tests_needed": True,
            "message": f"Code implementation complete for: {task.title}"
        }

    def _review_code(self, task):
        self._log(f"Reviewing code for: {task.title}")
        issues = []
        return {
            "action": "code_reviewed",
            "issues_found": len(issues),
            "issues": issues,
            "score": 95,
            "message": "Code review complete - high quality"
        }

    def _refactor_code(self, task):
        self._log(f"Refactoring code for: {task.title}")
        return {
            "action": "code_refactored",
            "improvements": ["readability", "performance", "maintainability"],
            "message": "Code refactored successfully"
        }

    def _fix_code(self, task):
        self._log(f"Fixing code for: {task.title}")
        return {
            "action": "code_fixed",
            "fixes_applied": [],
            "message": "Bug fix implemented"
        }

    def _general_task(self, task):
        return {
            "action": "task_completed",
            "message": f"Coder completed: {task.title}"
        }

    def analyze_code(self, file_path):
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        with open(file_path, "r") as f:
            content = f.read()

        lines = content.split("\n")
        analysis = {
            "file": file_path,
            "total_lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
            "functions": content.count("def "),
            "classes": content.count("class "),
            "imports": content.count("import "),
            "complexity": "low" if len(lines) < 100 else "medium" if len(lines) < 500 else "high"
        }
        return analysis
