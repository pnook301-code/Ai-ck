"""CK-NEXUS Full System - integrates everything"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexus_engine import NexusEngine
from agents.agent_manager import AgentManager


class NexusFullSystem:
    def __init__(self, config_dir=None):
        self.engine = NexusEngine(config_dir)
        self.agent_manager = AgentManager()

    def chat(self, message):
        return self.engine.chat(message)

    def execute_task(self, objective):
        return self.agent_manager.execute(objective)

    def delegate(self, agent_name, task):
        return self.agent_manager.delegate(agent_name, task)

    def run_audit(self):
        return self.agent_manager.run_full_audit()

    def get_status(self):
        return {
            "engine": {
                "session": self.engine.session_id,
                "providers": self.engine.router.get_status(),
                "line": self.engine.line_auth.get_status(),
                "memory": self.engine.memory.get_stats()
            },
            "agents": self.agent_manager.get_status()
        }

    def process_input(self, raw_input):
        # Route to agents if starts with @
        if raw_input.startswith("@"):
            parts = raw_input[1:].split(maxsplit=1)
            if len(parts) >= 2:
                agent_name = parts[0]
                task = parts[1]
                return self.delegate(agent_name, task)
            return self.execute_task(raw_input[1:])

        # Route to agent system if starts with /
        if raw_input.startswith("/agent"):
            return self.get_status()

        # Default to engine
        return self.engine.process_input(raw_input)

    def shutdown(self):
        self.engine.shutdown()
