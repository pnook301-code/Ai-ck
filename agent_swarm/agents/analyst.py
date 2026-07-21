"""
Analyst Agent — เชี่ยวชาญการวิเคราะห์ข้อมูล
"""

from .base_agent import BaseAgent, AgentMessage
from typing import Dict
from collections import Counter


class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="analyst",
            specialties=["analysis", "data_analysis", "metrics", "reporting"],
            model_preference="openrouter-nemotron-550b",
        )

    def on_message(self, msg: AgentMessage):
        if msg.topic == "analysis_request":
            result = self.work(msg.content, msg.data)
            self.send(to=msg.sender, topic="analysis_result", content=result, reply_to=msg.id)

    def work(self, task: str, context: Dict = None) -> str:
        """วิเคราะห์ข้อมูล — ใช้ LLM จริง"""
        self._task_count += 1
        data = (context or {}).get("data", {})

        # Use real LLM
        prompt = f"Analyze the following and provide detailed insights with metrics: {task}"
        analysis = self.call_llm(prompt, task_type="analysis")

        self.save_memory(f"analysis_{self._task_count}", {"task": task, "analysis": analysis}, tags=["analysis"])
        return f"[Analyst] Analysis:\n{analysis}"

    def _analyze(self, task: str, data: Dict) -> str:
        if data:
            keys = list(data.keys())
            return f"Data has {len(keys)} fields: {', '.join(keys[:5])}\nTask: {task[:80]}"
        return f"Analysis for: {task[:80]}\n- Need data to analyze\n- Recommend collecting metrics"

    def analyze_problem(self, problem: str) -> str:
        return (
            f"[Analyst] มุมมองด้านข้อมูล:\n"
            f"- ต้องรวบรวม metrics\n"
            f"- ต้องวิเคราะห์ root cause\n"
            f"- ต้องสรุป insight ที่ actionable"
        )

    def compare_options(self, options: Dict[str, str]) -> str:
        """เปรียบเทียบตัวเลือก"""
        lines = ["[Analyst] Comparison:"]
        for name, desc in options.items():
            lines.append(f"  • {name}: {desc[:60]}")
        return "\n".join(lines)
