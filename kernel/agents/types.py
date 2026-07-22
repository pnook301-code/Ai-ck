from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import time
import uuid


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    ERROR = "error"
    STOPPED = "stopped"


class AgentCapability(Enum):
    CODE_WRITE = "write_code"
    CODE_REVIEW = "review_code"
    CODE_REFACTOR = "refactor"
    CODE_DEBUG = "debug"
    TEST_EXECUTE = "test_execute"
    TEST_CREATE = "test_create"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    RESEARCH = "research"
    SECURITY_AUDIT = "security_audit"
    VULN_SCAN = "vuln_scan"
    REVIEW = "review"
    PLAN = "plan"
    COORDINATE = "coordinate"
    REPORT = "report"


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    msg_type: str
    content: Dict[str, Any]
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    task_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "sender": self.sender, "receiver": self.receiver,
            "type": self.msg_type, "content": self.content,
            "task_id": self.task_id, "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            sender=data["sender"], receiver=data["receiver"],
            msg_type=data["type"], content=data.get("content", {}),
            id=data.get("id"), task_id=data.get("task_id"),
        )


@dataclass
class AgentTask:
    title: str
    description: str
    priority: str = "medium"
    assigned_to: Optional[str] = None
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    status: str = "pending"
    result: Any = None
    subtasks: List["AgentTask"] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, result: Any):
        self.status = "completed"
        self.result = result
        self.completed_at = time.time()

    def fail(self, error: str):
        self.status = "failed"
        self.result = {"error": error}
        self.completed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "priority": self.priority, "status": self.status,
            "assigned_to": self.assigned_to, "result": self.result,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "created_at": self.created_at, "completed_at": self.completed_at,
        }
