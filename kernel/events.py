"""Event Bus - async event processing"""
from typing import Any, Callable, Dict, List, Optional, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import uuid
import logging


@dataclass
class Event:
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    source: str = "kernel"


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Async event bus with pub/sub pattern"""

    def __init__(self, logger: Any = None):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._logger = logger
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        self._running = True
        if self._logger:
            self._logger.debug("EventBus started")

    async def stop(self):
        self._running = False
        remaining = []
        while not self._queue.empty():
            try:
                remaining.append(await self._queue.get())
            except asyncio.QueueEmpty:
                break
        if remaining and self._logger:
            self._logger.debug(f"Drained {len(remaining)} events on stop")

    def on(self, event_name: str, handler: EventHandler):
        if event_name == "*":
            self._wildcard_handlers.append(handler)
        else:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            self._handlers[event_name].append(handler)

    def off(self, event_name: str, handler: EventHandler = None):
        if handler:
            handlers = self._handlers.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)
        else:
            self._handlers.pop(event_name, None)

    def once(self, event_name: str, handler: EventHandler):
        async def wrapper(event: Event):
            await handler(event)
            self.off(event_name, wrapper)
        self.on(event_name, wrapper)

    async def emit(self, event_name: str, data: Dict[str, Any] = None):
        event = Event(name=event_name, data=data or {})
        tasks = []

        for handler in self._wildcard_handlers:
            tasks.append(self._safe_dispatch(handler, event))

        handlers = self._handlers.get(event_name, [])
        for handler in handlers:
            tasks.append(self._safe_dispatch(handler, event))

        parts = event_name.rsplit(".", 1)
        if len(parts) > 1:
            parent = parts[0]
            parent_handlers = self._handlers.get(parent, [])
            for handler in parent_handlers:
                tasks.append(self._safe_dispatch(handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def emit_async(self, event_name: str, data: Dict[str, Any] = None):
        await self._queue.put((event_name, data or {}))
        self._tasks[:] = [t for t in self._tasks if not t.done()]
        if self._running:
            task = asyncio.create_task(self._process_queue())
            self._tasks.append(task)

    async def _process_queue(self):
        try:
            event_name, data = await self._queue.get()
            await self.emit(event_name, data)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Event queue error: {e}")

    async def _safe_dispatch(self, handler: EventHandler, event: Event):
        try:
            await handler(event)
        except Exception as e:
            if self._logger:
                self._logger.error(
                    f"Handler error for {event.name} — handler={getattr(handler, '__name__', '?')}: {e}"
                )
            else:
                import traceback
                traceback.print_exc()

    def listeners(self, event_name: str = None) -> int:
        if event_name:
            return len(self._handlers.get(event_name, []))
        return sum(len(h) for h in self._handlers.values()) + len(self._wildcard_handlers)
