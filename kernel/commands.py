"""Command Bus - command pattern dispatch"""
from typing import Any, Callable, Dict, Optional, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import uuid
import time
import logging


@dataclass
class Command:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: time.time())
    metadata: Dict[str, Any] = field(default_factory=dict)


CommandHandler = Callable[[Command], Awaitable[Any]]


@dataclass
class CommandResult:
    success: bool
    command: Command
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: float = field(default_factory=time.time)


class CommandBus:
    """Command bus with middleware support"""

    def __init__(self, event_bus: Any = None, logger: Any = None):
        self._handlers: Dict[str, CommandHandler] = {}
        self._middleware: list = []
        self._event_bus = event_bus
        self._logger = logger
        self._history: CommandResult = []

    def register(self, command_name: str, handler: CommandHandler):
        self._handlers[command_name] = handler

    def unregister(self, command_name: str):
        self._handlers.pop(command_name, None)

    def use(self, middleware: Callable):
        self._middleware.append(middleware)

    async def dispatch(self, command: Command) -> CommandResult:
        start = time.time()
        handler = self._handlers.get(command.name)

        if not handler:
            result = CommandResult(
                success=False,
                command=command,
                error=f"No handler for command: {command.name}",
                duration_ms=(time.time() - start) * 1000,
            )
            self._history.append(result)
            return result

        try:
            chain = self._build_chain(handler)
            result_data = await chain(command)

            result = CommandResult(
                success=True,
                command=command,
                result=result_data,
                duration_ms=(time.time() - start) * 1000,
            )
            self._history.append(result)

            if self._event_bus:
                await self._event_bus.emit("command.completed", {
                    "command": command.name,
                    "success": True,
                    "duration_ms": result.duration_ms,
                })

            return result

        except Exception as e:
            result = CommandResult(
                success=False,
                command=command,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )
            self._history.append(result)

            if self._event_bus:
                await self._event_bus.emit("command.failed", {
                    "command": command.name,
                    "error": str(e),
                    "duration_ms": result.duration_ms,
                })

            return result

    async def dispatch_sync(self, command_name: str, payload: Dict[str, Any] = None) -> CommandResult:
        return await self.dispatch(Command(name=command_name, payload=payload or {}))

    def _build_chain(self, handler: CommandHandler) -> CommandHandler:
        chain = handler
        for middleware in reversed(self._middleware):
            next_handler = chain
            chain = lambda cmd, m=middleware, n=next_handler: m(cmd, n)
        return chain

    def has_handler(self, command_name: str) -> bool:
        return command_name in self._handlers

    def get_history(self, limit: int = 10) -> CommandResult:
        return self._history[-limit:]

    def clear_history(self):
        self._history.clear()
