"""Agent Base - core agent class with communication protocol"""
import json
import time
import uuid
import os
from datetime import datetime


class AgentMessage:
    def __init__(self, sender, receiver, msg_type, content, task_id=None):
        self.id = f"msg_{uuid.uuid4().hex[:12]}"
        self.sender = sender
        self.receiver = receiver
        self.msg_type = msg_type
        self.content = content
        self.task_id = task_id
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id, "sender": self.sender, "receiver": self.receiver,
            "type": self.msg_type, "content": self.content,
            "task_id": self.task_id, "timestamp": self.timestamp
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        msg = cls(data["sender"], data["receiver"], data["type"], data["content"])
        msg.id = data.get("id", msg.id)
        msg.task_id = data.get("task_id")
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg


class AgentTask:
    def __init__(self, title, description, priority="medium", assigned_to=None):
        self.id = f"task_{uuid.uuid4().hex[:12]}"
        self.title = title
        self.description = description
        self.priority = priority
        self.status = "pending"
        self.assigned_to = assigned_to
        self.result = None
        self.subtasks = []
        self.created_at = datetime.now().isoformat()
        self.completed_at = None

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "priority": self.priority, "status": self.status,
            "assigned_to": self.assigned_to, "result": self.result,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "created_at": self.created_at, "completed_at": self.completed_at
        }

    def complete(self, result):
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now().isoformat()

    def fail(self, error):
        self.status = "failed"
        self.result = {"error": error}
        self.completed_at = datetime.now().isoformat()


class BaseAgent:
    def __init__(self, name, role, capabilities=None):
        self.name = name
        self.role = role
        self.capabilities = capabilities or []
        self.status = "idle"
        self.inbox = []
        self.outbox = []
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.created_at = datetime.now().isoformat()
        self.log = []

    def receive(self, message):
        self.inbox.append(message)
        self._log(f"Received: {message.msg_type} from {message.sender}")

    def send(self, receiver, msg_type, content, task_id=None):
        msg = AgentMessage(self.name, receiver, msg_type, content, task_id)
        self.outbox.append(msg)
        self._log(f"Sent: {msg_type} to {receiver}")
        return msg

    def execute(self, task):
        self.status = "working"
        self._log(f"Starting task: {task.title}")
        try:
            result = self._do_task(task)
            task.complete(result)
            self.tasks_completed += 1
            self._log(f"Completed: {task.title}")
        except Exception as e:
            task.fail(str(e))
            self.tasks_failed += 1
            self._log(f"Failed: {task.title} - {e}")
        self.status = "idle"
        return task

    def _do_task(self, task):
        raise NotImplementedError

    def _log(self, entry):
        self.log.append({
            "time": datetime.now().isoformat(),
            "entry": entry
        })

    def get_status(self):
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "capabilities": self.capabilities,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "inbox_size": len(self.inbox),
            "outbox_size": len(self.outbox),
            "log_entries": len(self.log)
        }

    def get_recent_log(self, limit=10):
        return self.log[-limit:]
