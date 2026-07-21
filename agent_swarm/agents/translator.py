"""
Translator Agent — เชี่ยวชาญการแปลภาษา
"""

from .base_agent import BaseAgent, AgentMessage
from typing import Dict


class TranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="translator",
            specialties=["translation", "localization", "language"],
            model_preference="openrouter-tencent-hy3",
        )

    def on_message(self, msg: AgentMessage):
        if msg.topic == "translate_request":
            target_lang = msg.data.get("target_lang", "en")
            result = self.work(msg.content, {"target_lang": target_lang})
            self.send(to=msg.sender, topic="translate_result", content=result, reply_to=msg.id)

    def work(self, task: str, context: Dict = None) -> str:
        """แปลภาษา"""
        self._task_count += 1
        target = (context or {}).get("target_lang", "en")
        result = self._translate(task, target)
        self.save_memory(f"translation_{self._task_count}", {"input": task, "output": result, "lang": target}, tags=["translation"])
        return f"[Translator] ({target}):\n{result}"

    def _translate(self, text: str, target: str) -> str:
        lang_names = {"th": "Thai", "en": "English", "ja": "Japanese", "zh": "Chinese"}
        return f"[{lang_names.get(target, target)}] {text}"

    def analyze_problem(self, problem: str) -> str:
        return (
            f"[Translator] มุมมองด้านภาษา:\n"
            f"- ต้องเข้าใจ context ทางวัฒนธรรม\n"
            f"- ต้องรักษาความหมายเดิม\n"
            f"- ต้องใช้ภาษาที่เป็นธรรมชาติ"
        )
