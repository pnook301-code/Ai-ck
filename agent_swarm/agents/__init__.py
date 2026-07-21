from .base_agent import BaseAgent, AgentMessage
from .researcher import ResearcherAgent
from .coder import CoderAgent
from .writer import WriterAgent
from .analyst import AnalystAgent
from .translator import TranslatorAgent
from .creator import CreatorAgent

ALL_AGENTS = [
    ResearcherAgent,
    CoderAgent,
    WriterAgent,
    AnalystAgent,
    TranslatorAgent,
    CreatorAgent,
]

def create_all_agents():
    """Instantiate all 6 agents."""
    return [cls() for cls in ALL_AGENTS]

__all__ = [
    'BaseAgent', 'AgentMessage',
    'ResearcherAgent', 'CoderAgent', 'WriterAgent',
    'AnalystAgent', 'TranslatorAgent', 'CreatorAgent',
    'ALL_AGENTS', 'create_all_agents',
]
