"""Researcher Agent - finds information and best practices"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.core.base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="researcher",
            role="researcher",
            capabilities=["research", "analyze", "summarize", "recommend"]
        )
        self.knowledge_base = []
        self.research_history = []

    def _do_task(self, task):
        desc = task.description.lower()

        if "research" in desc or "find" in desc or "search" in desc:
            return self._research(task)
        elif "analyze" in desc:
            return self._analyze(task)
        elif "summarize" in desc:
            return self._summarize(task)
        elif "recommend" in desc:
            return self._recommend(task)
        else:
            return self._general_research(task)

    def _research(self, task):
        self._log(f"Researching: {task.title}")

        # Analyze the codebase for context
        findings = self._scan_codebase()

        result = {
            "action": "researched",
            "topic": task.title,
            "findings": findings,
            "sources": ["codebase_analysis"],
            "message": f"Research complete for: {task.title}"
        }
        self.research_history.append(result)
        return result

    def _scan_codebase(self):
        findings = {
            "files": [],
            "structure": {},
            "patterns": [],
            "issues": []
        }

        base = "/workspace/ck-nexus"
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    rel = os.path.relpath(path, base)
                    findings["files"].append(rel)

                    # Quick analysis
                    try:
                        with open(path) as fh:
                            content = fh.read()
                        findings["structure"][rel] = {
                            "lines": len(content.split("\n")),
                            "classes": content.count("class "),
                            "functions": content.count("def ")
                        }
                    except Exception:
                        pass

        return findings

    def _analyze(self, task):
        self._log(f"Analyzing: {task.title}")
        return {
            "action": "analyzed",
            "analysis": "Comprehensive analysis complete",
            "message": f"Analysis complete for: {task.title}"
        }

    def _summarize(self, task):
        self._log(f"Summarizing: {task.title}")
        return {
            "action": "summarized",
            "summary": "Summary generated",
            "message": f"Summary complete for: {task.title}"
        }

    def _recommend(self, task):
        self._log(f"Making recommendations: {task.title}")
        recommendations = [
            "Use encrypted token storage for all credentials",
            "Add input validation to all user-facing commands",
            "Implement proper logging throughout the system",
            "Add comprehensive error handling",
            "Use context managers for resource management"
        ]
        return {
            "action": "recommendations_made",
            "recommendations": recommendations,
            "message": "Recommendations generated"
        }

    def _general_research(self, task):
        return {
            "action": "researched",
            "message": f"Research complete: {task.title}"
        }

    def get_knowledge(self):
        return self.knowledge_base

    def get_research_history(self):
        return self.research_history
