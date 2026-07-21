"""
Creator Agent — เชี่ยวชาญการสร้างสรรค์ (UI, UX, Design, Ideas)
"""

from .base_agent import BaseAgent, AgentMessage
from typing import Dict


class CreatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="creator",
            specialties=["creative", "design", "brainstorming", "innovation"],
            model_preference="openrouter-gemma4-31b",
        )
        self._ideas = []

    def on_message(self, msg: AgentMessage):
        if msg.topic == "create_request":
            result = self.work(msg.content, msg.data)
            self.send(to=msg.sender, topic="create_result", content=result, reply_to=msg.id)
        elif msg.topic == "brainstorm_request":
            ideas = self.brainstorm(msg.content)
            self.send(to=msg.sender, topic="brainstorm_result", content=ideas, reply_to=msg.id)

    def work(self, task: str, context: Dict = None) -> str:
        """สร้างสรรค์ผลงาน — ใช้ LLM จริง"""
        self._task_count += 1

        # Use real LLM
        prompt = f"Generate creative ideas and innovative solutions for: {task}. Think outside the box."
        idea = self.call_llm(prompt, task_type="creative")

        self._ideas.append(idea)
        self.save_memory(f"creation_{self._task_count}", {"task": task, "idea": idea}, tags=["creative"])
        return f"[Creator] Creative output:\n{idea}"

    def _create(self, task: str, context: Dict = None) -> str:
        return (
            f"💡 Creative Concept for: {task[:60]}\n\n"
            f"## Idea\n"
            f"Think outside the box — combine unexpected elements.\n\n"
            f"## Approach\n"
            f"1. Start with user empathy\n"
            f"2. Prototype quickly\n"
            f"3. Iterate based on feedback"
        )

    def brainstorm(self, topic: str) -> str:
        ideas = [
            f"🔹 {topic} with AI-powered automation",
            f"🔹 {topic} with gamification",
            f"🔹 {topic} as a marketplace",
            f"🔹 {topic} with community-driven approach",
        ]
        return "[Creator] Brainstorm:\n" + "\n".join(ideas)

    def analyze_problem(self, problem: str) -> str:
        return (
            f"[Creator] มุมมองด้านความสร้างสรรค์:\n"
            f"- ต้องคิดนอกกรอบ\n"
            f"- ต้องเชื่อมโยงสิ่งที่ดูเหมือนไม่เกี่ยวข้อง\n"
            f"- ต้องลอง prototyping เร็ว"
        )
