"""
Writer Agent — เชี่ยวชาญการเขียน (บทความ, เนื้อหา, เอกสาร)
"""

from .base_agent import BaseAgent, AgentMessage
from typing import Dict


class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="writer",
            specialties=["writing", "documentation", "content_creation", "summarization"],
            model_preference="openrouter-gemma4-31b",
        )

    def on_message(self, msg: AgentMessage):
        if msg.topic == "write_request":
            result = self.work(msg.content, msg.data)
            self.send(to=msg.sender, topic="write_result", content=result, reply_to=msg.id)
        elif msg.topic == "summarize_request":
            result = self.summarize(msg.content)
            self.send(to=msg.sender, topic="summary_result", content=result, reply_to=msg.id)

    def work(self, task: str, context: Dict = None) -> str:
        """เขียนเนื้อหาตาม task — ใช้ LLM จริง"""
        self._task_count += 1
        style = (context or {}).get("style", "professional")

        # Use real LLM
        prompt = f"Write a {style} article about: {task}. Include introduction, key points, and conclusion."
        article = self.call_llm(prompt, task_type="creative")

        self.save_memory(f"writing_{self._task_count}", {"task": task, "content": article}, tags=["writing"])
        return f"[Writer] Article ({style}):\n{article}"

    def _write_article(self, topic: str, style: str) -> str:
        return (
            f"# {topic}\n\n"
            f"## Introduction\n"
            f"This article explores {topic[:80]}...\n\n"
            f"## Key Points\n"
            f"1. First important aspect\n"
            f"2. Technical considerations\n"
            f"3. Practical applications\n\n"
            f"## Conclusion\n"
            f"In summary, {topic[:50]} is a fascinating topic."
        )

    def summarize(self, text: str) -> str:
        words = text.split()[:50]
        return f"[Summary] {' '.join(words)}..."

    def analyze_problem(self, problem: str) -> str:
        return (
            f"[Writer] มุมมองด้านการสื่อสาร:\n"
            f"- ต้องเข้าใจ audience\n"
            f"- ต้องใช้ภาษาที่ชัดเจน\n"
            f"- ต้องมี structure ที่ดี"
        )
