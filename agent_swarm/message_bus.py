"""
EventBus — Message Bus สำหรับ Agent-to-Agent Communication
ทุก Agent สื่อสารกันผ่าน Event นี้
"""

import time
import uuid
import threading
import logging
from typing import Dict, List, Any, Callable, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from queue import Queue

logger = logging.getLogger("NEXUS-EventBus")


@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    sender: str = ""
    receiver: str = ""  # "" = broadcast
    data: Dict = field(default_factory=dict)
    reply_to: str = ""
    timestamp: float = field(default_factory=time.time)
    priority: int = 5  # 1=highest, 10=lowest
    ttl: float = 30.0  # seconds before auto-expire


class EventBus:
    """Central Message Bus for Agent Swarm"""

    def __init__(self, max_queue_size: int = 10000):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._wildcard_handlers: List[Callable] = []
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._running = False
        self._lock = threading.RLock()
        self._history: List[Dict] = []
        self._max_history = 1000
        self._stats = {
            "total_emitted": 0,
            "total_delivered": 0,
            "total_dropped": 0,
            "by_topic": defaultdict(int),
            "by_sender": defaultdict(int),
        }
        self._processor_thread: Optional[threading.Thread] = None

    def on(self, topic: str, handler: Callable):
        """Register handler for topic. Use '*' for wildcard."""
        with self._lock:
            if topic == "*":
                self._wildcard_handlers.append(handler)
            else:
                self._handlers[topic].append(handler)
            logger.debug(f"Registered handler for '{topic}': {handler.__name__}")

    def off(self, topic: str, handler: Callable):
        """Unregister handler."""
        with self._lock:
            if topic == "*":
                self._wildcard_handlers.remove(handler)
            elif topic in self._handlers:
                self._handlers[topic].remove(handler)

    def emit(self, topic: str, data: Dict = None, sender: str = "",
             receiver: str = "", reply_to: str = "", priority: int = 5):
        """Emit event to bus."""
        event = Event(
            topic=topic,
            sender=sender,
            receiver=receiver,
            data=data or {},
            reply_to=reply_to,
            priority=priority,
        )

        # History
        with self._lock:
            self._history.append({
                "id": event.id,
                "topic": topic,
                "sender": sender,
                "receiver": receiver,
                "ts": event.timestamp,
            })
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        # Stats
        self._stats["total_emitted"] += 1
        self._stats["by_topic"][topic] += 1
        if sender:
            self._stats["by_sender"][sender] += 1

        # Enqueue
        try:
            self._queue.put_nowait(event)
        except Exception:
            self._stats["total_dropped"] += 1
            logger.warning(f"Queue full, dropped event: {topic}")

    def emit_sync(self, topic: str, data: Dict = None, sender: str = "",
                  receiver: str = "", reply_to: str = ""):
        """Emit and deliver immediately (blocking)."""
        event = Event(
            topic=topic, sender=sender, receiver=receiver,
            data=data or {}, reply_to=reply_to,
        )
        self._deliver(event)

    def _deliver(self, event: Event):
        """Deliver event to matching handlers."""
        delivered = False

        # Direct topic handlers
        with self._lock:
            handlers = list(self._handlers.get(event.topic, []))

        for handler in handlers:
            try:
                if event.receiver and event.sender == event.receiver:
                    continue  # Don't deliver to self
                handler(event)
                delivered = True
                self._stats["total_delivered"] += 1
            except Exception as e:
                logger.error(f"Handler error on '{event.topic}': {e}")

        # Wildcard handlers
        with self._lock:
            wc_handlers = list(self._wildcard_handlers)

        for handler in wc_handlers:
            try:
                handler(event)
                delivered = True
            except Exception as e:
                logger.error(f"Wildcard handler error: {e}")

        if not delivered:
            logger.debug(f"No handlers for topic: {event.topic}")

    def _process_loop(self):
        """Background loop to deliver events."""
        while self._running:
            try:
                event = self._queue.get(timeout=0.1)
                # Check TTL
                if time.time() - event.timestamp > event.ttl:
                    self._stats["total_dropped"] += 1
                    continue
                self._deliver(event)
            except Exception:
                continue

    def start(self):
        """Start background processor."""
        if self._running:
            return
        self._running = True
        self._processor_thread = threading.Thread(
            target=self._process_loop, daemon=True, name="eventbus-processor"
        )
        self._processor_thread.start()
        logger.info("🚀 EventBus STARTED")

    def stop(self):
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=2)
        logger.info("🛑 EventBus STOPPED")

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                **self._stats,
                "queue_size": self._queue.qsize(),
                "handlers": {t: len(h) for t, h in self._handlers.items()},
            }

    def get_history(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            return self._history[-limit:]


# Global instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
