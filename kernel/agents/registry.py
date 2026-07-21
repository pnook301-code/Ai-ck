"""Agent Registry - manages agent registration and discovery"""
from typing import Any, Dict, List, Optional, Set
from .base import BaseAgent
from .types import AgentCapability


class AgentRegistry:
    def __init__(self, logger: Any = None):
        self._agents: Dict[str, BaseAgent] = {}
        self._logger = logger

    def register(self, agent: BaseAgent):
        self._agents[agent.name] = agent
        if self._logger:
            self._logger.info(f"Agent registered: {agent.name} ({agent.role})")

    def unregister(self, name: str):
        self._agents.pop(name, None)

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def list_agents(self) -> List[BaseAgent]:
        return list(self._agents.values())

    def find_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        return [a for a in self._agents.values() if capability in a.capabilities]

    def find_by_role(self, role: str) -> List[BaseAgent]:
        return [a for a in self._agents.values() if a.role == role]

    def get_names(self) -> List[str]:
        return list(self._agents.keys())

    def count(self) -> int:
        return len(self._agents)

    def get_all_status(self) -> Dict[str, Any]:
        return {name: agent.get_status() for name, agent in self._agents.items()}
