"""Lifecycle Management - service lifecycle phases"""
from typing import Any, Callable, Dict, List, Optional, Awaitable
from enum import Enum
from dataclasses import dataclass, field
import asyncio


class LifecyclePhase(Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    STARTED = "started"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    DESTROYED = "destroyed"
    ERROR = "error"


LifecycleHook = Callable[[], Awaitable[None]]


@dataclass
class LifecycleComponent:
    name: str
    phase: LifecyclePhase = LifecyclePhase.CREATED
    on_init: Optional[LifecycleHook] = None
    on_start: Optional[LifecycleHook] = None
    on_stop: Optional[LifecycleHook] = None
    on_destroy: Optional[LifecycleHook] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class LifecycleManager:
    """Manages lifecycle phases for all components"""

    def __init__(self, logger: Any = None):
        self._components: Dict[str, LifecycleComponent] = {}
        self._phase = LifecyclePhase.CREATED
        self._logger = logger
        self._phase_hooks: Dict[LifecyclePhase, List[LifecycleHook]] = {}

    def register(self, component: LifecycleComponent):
        self._components[component.name] = component
        if self._logger:
            self._logger.debug(f"Registered lifecycle component: {component.name}")

    def unregister(self, name: str):
        self._components.pop(name, None)

    def on_phase(self, phase: LifecyclePhase, hook: LifecycleHook):
        if phase not in self._phase_hooks:
            self._phase_hooks[phase] = []
        self._phase_hooks[phase].append(hook)

    async def initialize_all(self, parallel: bool = True):
        self._phase = LifecyclePhase.INITIALIZING
        await self._run_hooks(LifecyclePhase.INITIALIZING)
        if parallel:
            tasks = [self._init_component(c) for c in self._components.values() if c.on_init]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for component in self._components.values():
                if component.on_init:
                    await self._init_component(component)
        self._phase = LifecyclePhase.INITIALIZED
        await self._run_hooks(LifecyclePhase.INITIALIZED)

    async def start_all(self, parallel: bool = True):
        self._phase = LifecyclePhase.STARTING
        await self._run_hooks(LifecyclePhase.STARTING)
        if parallel:
            tasks = [self._start_component(c) for c in self._components.values() if c.on_start]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for component in self._components.values():
                if component.on_start:
                    await self._start_component(component)
        self._phase = LifecyclePhase.STARTED
        await self._run_hooks(LifecyclePhase.STARTED)
        self._phase = LifecyclePhase.READY
        await self._run_hooks(LifecyclePhase.READY)

    async def stop_all(self, parallel: bool = True):
        self._phase = LifecyclePhase.STOPPING
        await self._run_hooks(LifecyclePhase.STOPPING)
        if parallel:
            tasks = [self._stop_component(c) for c in reversed(list(self._components.values())) if c.on_stop]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            for component in reversed(list(self._components.values())):
                if component.on_stop:
                    await self._stop_component(component)
        self._phase = LifecyclePhase.STOPPED
        await self._run_hooks(LifecyclePhase.STOPPED)

    async def destroy_all(self):
        await self.stop_all()
        for component in self._components.values():
            if component.on_destroy:
                try:
                    await component.on_destroy()
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"Destroy error for {component.name}: {e}")
            component.phase = LifecyclePhase.DESTROYED
        self._phase = LifecyclePhase.DESTROYED

    async def _init_component(self, component: LifecycleComponent):
        try:
            component.phase = LifecyclePhase.INITIALIZING
            await component.on_init()
            component.phase = LifecyclePhase.INITIALIZED
        except Exception as e:
            component.phase = LifecyclePhase.ERROR
            component.error = str(e)
            if self._logger:
                self._logger.error(f"Init failed for {component.name}: {e}")

    async def _start_component(self, component: LifecycleComponent):
        try:
            component.phase = LifecyclePhase.STARTING
            await component.on_start()
            component.phase = LifecyclePhase.STARTED
        except Exception as e:
            component.phase = LifecyclePhase.ERROR
            component.error = str(e)
            if self._logger:
                self._logger.error(f"Start failed for {component.name}: {e}")

    async def _stop_component(self, component: LifecycleComponent):
        try:
            component.phase = LifecyclePhase.STOPPING
            await component.on_stop()
            component.phase = LifecyclePhase.STOPPED
        except Exception as e:
            component.phase = LifecyclePhase.ERROR
            component.error = str(e)

    async def _run_hooks(self, phase: LifecyclePhase):
        hooks = self._phase_hooks.get(phase, [])
        for hook in hooks:
            try:
                await hook()
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Phase hook error for {phase.value}: {e}")

    def get_phase(self) -> LifecyclePhase:
        return self._phase

    def get_component(self, name: str) -> Optional[LifecycleComponent]:
        return self._components.get(name)

    def summary(self) -> Dict[str, Any]:
        return {
            "phase": self._phase.value,
            "components": {
                name: {"phase": c.phase.value, "error": c.error}
                for name, c in self._components.items()
            },
        }
