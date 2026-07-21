"""
BaseAgent — พื้นฐานสำหรับ Agent ทุกตัว
"""

import time
import uuid
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.vector_memory import get_vector_memory

logger = logging.getLogger("NEXUS-Agent")


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""
    receiver: str = ""
    topic: str = ""
    content: str = ""
    data: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reply_to: str = ""


class BaseAgent(ABC):
    """Base class for all swarm agents."""

    def __init__(self, name: str, specialties: List[str] = None,
                 model_preference: str = None):
        self.name = name
        self.specialties = specialties or []
        self.model_preference = model_preference
        self.is_running = False
        self._task_count = 0
        self._error_count = 0
        self._inbox: List[AgentMessage] = []
        self._lock = threading.RLock()

        # Lazy import to avoid circular imports
        self._event_bus = None
        self._memory = None
        self._vector_memory = None

    @property
    def event_bus(self):
        if self._event_bus is None:
            from agent_swarm.message_bus import get_event_bus
            self._event_bus = get_event_bus()
        return self._event_bus

    @property
    def memory(self):
        if self._memory is None:
            from agent_swarm.shared_memory import get_shared_memory
            self._memory = get_shared_memory()
        return self._memory

    @property
    def vector_memory(self):
        if self._vector_memory is None:
            self._vector_memory = get_vector_memory()
        return self._vector_memory

    def start(self):
        """Start agent and register for events."""
        self.is_running = True
        # Listen for messages directed to this agent
        self.event_bus.on(f"agent:message.{self.name}", self._handle_message)
        self.event_bus.on("agent:broadcast", self._handle_broadcast)
        logger.info(f"🤖 Agent '{self.name}' started | specialties: {self.specialties}")

    def stop(self):
        self.is_running = False
        self.event_bus.off(f"agent:message.{self.name}", self._handle_message)
        self.event_bus.off("agent:broadcast", self._handle_broadcast)
        logger.info(f"🤖 Agent '{self.name}' stopped")

    def send(self, to: str, topic: str, content: str = "",
             data: Dict = None, reply_to: str = ""):
        """Send message to another agent."""
        msg = AgentMessage(
            sender=self.name, receiver=to, topic=topic,
            content=content, data=data or {}, reply_to=reply_to,
        )
        self.event_bus.emit(
            f"agent:message.{to}",
            data={"message": msg},
            sender=self.name,
            receiver=to,
        )

    def broadcast(self, topic: str, content: str = "", data: Dict = None):
        """Broadcast message to all agents."""
        self.event_bus.emit(
            "agent:broadcast",
            data={
                "message": AgentMessage(
                    sender=self.name, topic=topic,
                    content=content, data=data or {},
                )
            },
            sender=self.name,
        )

    def emit(self, topic: str, data: Dict = None):
        """Emit custom event."""
        self.event_bus.emit(topic, data=data or {}, sender=self.name)

    def save_memory(self, key: str, value: Any, ttl: float = 0,
                    tags: List[str] = None):
        """Save to shared memory."""
        self.memory.save(key, value, agent_name=self.name, ttl=ttl, tags=tags)

    def get_memory(self, key: str) -> Optional[Any]:
        """Read from shared memory."""
        return self.memory.get(key)

    def _handle_message(self, event):
        """Handle incoming message."""
        msg = event.data.get("message")
        if msg and msg.receiver == self.name:
            with self._lock:
                self._inbox.append(msg)
            self.on_message(msg)

    def _handle_broadcast(self, event):
        """Handle broadcast message."""
        msg = event.data.get("message")
        if msg and msg.sender != self.name:
            self.on_broadcast(msg)

    @abstractmethod
    def on_message(self, msg: AgentMessage):
        """Handle a message directed to this agent."""
        pass

    def on_broadcast(self, msg: AgentMessage):
        """Handle broadcast messages (override if needed)."""
        pass

    def call_llm(self, prompt: str, task_type: str = "general") -> str:
        """Call LLM via Multi-Model Orchestrator."""
        try:
            from multi_model_orchestrator import get_orchestrator, TaskType
            orch = get_orchestrator()
            task_type_enum = getattr(TaskType, task_type.upper(), TaskType.GENERAL)
            task_id = orch.submit_task(task_type_enum, prompt, priority=1)
            # Wait for result (quick poll)
            import time
            for _ in range(30):
                time.sleep(1)
                for t in orch.completed_tasks:
                    if t.id == task_id and t.result:
                        return t.result
            return f"[{self.name}] LLM timeout — using local fallback"
        except Exception as e:
            return f"[{self.name}] LLM unavailable: {e}"

    @abstractmethod
    def work(self, task: str, context: Dict = None) -> str:
        """Execute work. Must be implemented by each agent."""
        pass

    def recall_memory(self, query: str, top_k: int = 5):
        return self.vector_memory.search(query, top_k=top_k)

    def save_memory_os(self, content: str, metadata: dict = None):
        doc_id = self.vector_memory.add_document(
            content,
            metadata={"agent": self.name, **(metadata or {})}
        )
        return doc_id

    def analyze_problem(self, problem: str) -> str:
        """Analyze a problem from this agent's perspective.
        Override in subclass for specialized analysis."""
        return f"[{self.name}] Need more context to analyze: {problem[:100]}"

    def get_status(self) -> Dict:
        return {
            "name": self.name,
            "specialties": self.specialties,
            "model": self.model_preference,
            "running": self.is_running,
            "tasks_done": self._task_count,
            "errors": self._error_count,
            "inbox_size": len(self._inbox),
        }
