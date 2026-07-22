"""Task Scheduler - cron-like scheduling"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import asyncio
import time
import uuid


@dataclass
class ScheduledTask:
    name: str
    interval: float  # seconds
    callback: Callable = field(repr=False)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    enabled: bool = True
    run_immediately: bool = False
    max_executions: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _execution_count: int = 0
    _last_run: float = 0.0
    _next_run: float = 0.0
    _last_duration: float = 0.0


class TaskScheduler:
    """Schedule and run periodic tasks"""

    def __init__(self, logger: Any = None):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._logger = logger

    def register(self, task: ScheduledTask):
        task._next_run = time.time() + (0 if task.run_immediately else task.interval)
        self._tasks[task.id] = task

    def add(self, name: str, interval: float, callback: Callable, **kwargs) -> str:
        task = ScheduledTask(name=name, interval=interval, callback=callback, **kwargs)
        self.register(task)
        return task.id

    def unregister(self, task_id: str):
        self._tasks.pop(task_id, None)

    def start(self):
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except (asyncio.CancelledError, Exception):
                pass
            self._loop_task = None

    async def _run_loop(self):
        while self._running:
            now = time.time()
            for task in list(self._tasks.values()):
                if not task.enabled:
                    continue
                if task.max_executions and task._execution_count >= task.max_executions:
                    continue
                if now >= task._next_run:
                    asyncio.create_task(self._execute(task))
                    task._next_run = now + task.interval

            await asyncio.sleep(1)

    async def _execute(self, task: ScheduledTask):
        start = time.time()
        task._execution_count += 1
        try:
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback()
            else:
                task.callback()
            task._last_duration = (time.time() - start) * 1000
            task._last_run = time.time()
        except Exception as e:
            task._last_duration = (time.time() - start) * 1000
            task._last_run = time.time()
            if self._logger:
                self._logger.error(f"Task {task.name} failed: {e}")

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def get_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks.values())

    def pause(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.enabled = False

    def resume(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.enabled = True
            task._next_run = time.time() + task.interval

    def summary(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total": len(self._tasks),
            "enabled": sum(1 for t in self._tasks.values() if t.enabled),
            "tasks": [
                {
                    "name": t.name,
                    "interval": t.interval,
                    "enabled": t.enabled,
                    "executions": t._execution_count,
                    "last_run": t._last_run,
                    "next_run": t._next_run,
                    "last_duration_ms": t._last_duration,
                }
                for t in self._tasks.values()
            ],
        }
