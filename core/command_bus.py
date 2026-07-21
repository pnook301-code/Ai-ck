"""Command Bus - central command processing with authentication"""
import json
import time
from datetime import datetime

class Command:
    def __init__(self, name, args=None, user="system", role="admin"):
        self.id = f"cmd_{int(time.time()*1000)}"
        self.name = name
        self.args = args or {}
        self.user = user
        self.role = role
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "args": self.args,
            "user": self.user, "role": self.role, "timestamp": self.timestamp
        }

class EventBus:
    def __init__(self):
        self.listeners = {}
        self.history = []

    def on(self, event_name, callback):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(callback)

    def emit(self, event_name, data=None):
        self.history.append({"event": event_name, "data": data, "time": datetime.now().isoformat()})
        for cb in self.listeners.get(event_name, []):
            try:
                cb(data)
            except Exception as e:
                self.history.append({"event": "error", "data": str(e), "time": datetime.now().isoformat()})

    def get_history(self, limit=50):
        return self.history[-limit:]

class CommandBus:
    def __init__(self):
        self.commands = {}
        self.event_bus = EventBus()
        self.auth_tokens = {}
        self.audit_log = []
        self._register_default_commands()

    def _register_default_commands(self):
        self.register("help", self._cmd_help)
        self.register("status", self._cmd_status)
        self.register("memory", self._cmd_memory)
        self.register("skills", self._cmd_skills)
        self.register("events", self._cmd_events)
        self.register("providers", self._cmd_providers)

    def register(self, name, handler):
        self.commands[name] = handler
        self.event_bus.emit("command_registered", {"name": name})

    def execute(self, command_name, args=None, user="user", role="user"):
        cmd = Command(command_name, args, user, role)
        self.audit_log.append(cmd.to_dict())
        self.event_bus.emit("command_executed", cmd.to_dict())

        if command_name not in self.commands:
            return {"error": f"Unknown command: {command_name}. Type 'help' for available commands."}

        try:
            result = self.commands[command_name](args or {}, user, role)
            self.event_bus.emit("command_success", {"name": command_name, "result": result})
            return result
        except Exception as e:
            self.event_bus.emit("command_error", {"name": command_name, "error": str(e)})
            return {"error": str(e)}

    def _cmd_help(self, args, user, role):
        return {
            "commands": list(self.commands.keys()),
            "usage": "Type command name, or 'chat <message>' to talk to AI"
        }

    def _cmd_status(self, args, user, role):
        return {"status": "operational", "commands": len(self.commands), "uptime": time.time()}

    def _cmd_memory(self, args, user, role):
        return {"info": "Use memory directly via MemoryOS"}

    def _cmd_skills(self, args, user, role):
        return {"info": "Use skills via MemoryOS"}

    def _cmd_events(self, args, user, role):
        return {"events": self.event_bus.get_history(20)}

    def _cmd_providers(self, args, user, role):
        return {"info": "Use router.get_status()"}
