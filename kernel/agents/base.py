"""Base Agent - kernel-aware agent with EventBus integration"""
from typing import Any, Dict, List, Optional, Set
import time

from .types import AgentMessage, AgentTask, AgentStatus, AgentCapability


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        capabilities: Set[AgentCapability] = None,
        event_bus: Any = None,
        logger: Any = None,
    ):
        self.name = name
        self.role = role
        self.capabilities = capabilities or set()
        self.status = AgentStatus.IDLE
        self.inbox: List[AgentMessage] = []
        self.outbox: List[AgentMessage] = []
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.created_at = time.time()
        self.event_bus = event_bus
        self.logger = logger
        self._log: List[Dict] = []

    async def initialize(self):
        self.status = AgentStatus.IDLE
        if self.event_bus:
            await self.event_bus.emit("agent.initialized", {"name": self.name})
        self._log_entry(f"Initialized: {self.name}")

    async def receive(self, message: AgentMessage):
        self.inbox.append(message)
        self._log_entry(f"Received: {message.msg_type} from {message.sender}")

    async def send(self, receiver: str, msg_type: str, content: Dict[str, Any], task_id: str = None) -> AgentMessage:
        msg = AgentMessage(
            sender=self.name, receiver=receiver,
            msg_type=msg_type, content=content, task_id=task_id,
        )
        self.outbox.append(msg)
        self._log_entry(f"Sent: {msg_type} to {receiver}")
        if self.event_bus:
            await self.event_bus.emit("agent.message.sent", {
                "from": self.name, "to": receiver, "type": msg_type, "task_id": task_id,
            })
        return msg

    async def execute(self, task: AgentTask) -> AgentTask:
        self.status = AgentStatus.WORKING
        self._log_entry(f"Starting: {task.title}")
        if self.event_bus:
            await self.event_bus.emit("agent.task.started", {
                "agent": self.name, "task_id": task.id, "title": task.title,
            })
        try:
            result = await self._do_task(task)
            task.complete(result)
            self.tasks_completed += 1
            self._log_entry(f"Completed: {task.title}")
            if self.event_bus:
                await self.event_bus.emit("agent.task.completed", {
                    "agent": self.name, "task_id": task.id, "success": True,
                })
        except Exception as e:
            task.fail(str(e))
            self.tasks_failed += 1
            self._log_entry(f"Failed: {task.title} - {e}")
            if self.event_bus:
                await self.event_bus.emit("agent.task.failed", {
                    "agent": self.name, "task_id": task.id, "error": str(e),
                })
        self.status = AgentStatus.IDLE
        return task

    async def _do_task(self, task: AgentTask) -> Any:
        raise NotImplementedError

    def _log_entry(self, entry: str):
        self._log.append({"time": time.time(), "entry": entry})
        if self.logger:
            self.logger.debug(f"[{self.name}] {entry}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "inbox_size": len(self.inbox),
            "outbox_size": len(self.outbox),
            "uptime": time.time() - self.created_at,
        }

    def get_log(self, limit: int = 10) -> List[Dict]:
        return self._log[-limit:]

    async def stop(self):
        self.status = AgentStatus.STOPPED
        if self.event_bus:
            await self.event_bus.emit("agent.stopped", {"name": self.name})
