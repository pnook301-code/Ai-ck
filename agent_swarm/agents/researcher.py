"""
Researcher Agent — เชี่ยวชาญการค้นหาข้อมูล
"""

from .base_agent import BaseAgent, AgentMessage
from typing import Dict, Optional


class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="researcher",
            specialties=["research", "information_retrieval", "fact_checking"],
            model_preference="openrouter-nemotron-30b-reasoning",
        )
        self._sources = []

    def on_message(self, msg: AgentMessage):
        if msg.topic == "research_request":
            result = self.work(msg.content, msg.data)
            self.send(
                to=msg.sender,
                topic="research_result",
                content=result,
                reply_to=msg.id,
            )

    def work(self, task: str, context: Dict = None) -> str:
        """ค้นหาข้อมูลเกี่ยวกับ topic — ใช้ LLM จริง"""
        self._task_count += 1

        # Search shared memory first
        existing = self.memory.search(agent_name="researcher", limit=5)
        cached = [e for e in existing if task.lower() in e.get("key", "").lower()]

        if cached:
            return f"[Researcher] Found {len(cached)} cached results for: {task}"

        # Use real LLM for research
        prompt = f"Research and provide comprehensive findings on: {task}. Include key facts, trends, and sources."
        findings = self.call_llm(prompt, task_type="reasoning")

        self.save_memory(
            f"research_{task[:50]}",
            {"findings": findings, "status": "completed"},
            tags=["research", "findings"],
        )

        return f"[Researcher] Findings for: {task[:80]}\n{findings}"

    def _generate_research_plan(self, task: str) -> str:
        return (
            f"1. Identify key aspects of: {task}\n"
            f"2. Search authoritative sources\n"
            f"3. Cross-reference facts\n"
            f"4. Compile findings with citations"
        )

    def analyze_problem(self, problem: str) -> str:
        return (
            f"[Researcher] สำหรับปัญหานี้ ต้องการข้อมูลเพิ่มเติม:\n"
            f"- ต้องการ context เพิ่มเติม\n"
            f"- ต้องการ sources ที่เชื่อถือได้\n"
            f"- ต้องการ cross-reference กับข้อมูลอื่น"
        )
