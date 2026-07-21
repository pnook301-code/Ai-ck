"""Bootstrap Service - initialization sequences"""
from typing import Any, Callable, Dict, List, Optional, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging


@dataclass
class BootstrapPhase:
    name: str
    order: int
    handlers: List[Callable] = field(default_factory=list)
    required: bool = True
    timeout: float = 30.0
    phase_time: float = 0.0
    success: bool = False
    error: Optional[str] = None


class BootstrapService:
    """Manages ordered initialization phases"""

    def __init__(self, logger: Any = None):
        self._phases: Dict[str, BootstrapPhase] = {}
        self._results: Dict[str, bool] = {}
        self._logger = logger
        self._started = False

    def add_phase(self, name: str, order: int, required: bool = True, timeout: float = 30.0):
        if name in self._phases:
            return
        self._phases[name] = BootstrapPhase(
            name=name, order=order, required=required, timeout=timeout
        )

    def add_handler(self, phase_name: str, handler: Callable):
        phase = self._phases.get(phase_name)
        if phase:
            phase.handlers.append(handler)

    async def execute(self) -> bool:
        self._started = True
        sorted_phases = sorted(self._phases.values(), key=lambda p: p.order)

        for phase in sorted_phases:
            if not phase.handlers:
                phase.success = True
                self._results[phase.name] = True
                continue

            start = time.time()
            if self._logger:
                self._logger.info(f"Bootstrap phase: {phase.name}")

            try:
                tasks = []
                for handler in phase.handlers:
                    if asyncio.iscoroutinefunction(handler):
                        tasks.append(asyncio.wait_for(handler(), timeout=phase.timeout))
                    else:
                        tasks.append(asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, handler),
                            timeout=phase.timeout
                        ))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                errors = [r for r in results if isinstance(r, Exception)]
                if errors:
                    phase.error = "; ".join(str(e) for e in errors)
                    phase.success = False
                    self._results[phase.name] = False
                    if self._logger:
                        self._logger.error(f"Phase {phase.name} failed: {phase.error}")

                    if phase.required:
                        return False
                else:
                    phase.success = True
                    self._results[phase.name] = True

            except asyncio.TimeoutError:
                phase.error = f"Phase timed out after {phase.timeout}s"
                phase.success = False
                self._results[phase.name] = False
                if phase.required:
                    return False

            except Exception as e:
                phase.error = str(e)
                phase.success = False
                self._results[phase.name] = False
                if phase.required:
                    return False

            finally:
                phase.phase_time = (time.time() - start) * 1000

        return all(self._results.get(p.name, False) for p in sorted_phases if p.required)

    def get_results(self) -> Dict[str, Any]:
        return {
            name: {
                "success": phase.success,
                "error": phase.error,
                "duration_ms": phase.phase_time,
            }
            for name, phase in self._phases.items()
        }

    def is_healthy(self) -> bool:
        return self._started and all(
            p.success for p in self._phases.values() if p.required
        )
