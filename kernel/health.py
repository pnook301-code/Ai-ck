"""Health Checks - service health monitoring"""
from typing import Any, Callable, Dict, List, Optional, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import time


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    last_check: float = 0.0
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


HealthCheckHandler = Callable[[], Awaitable[HealthCheck]]


class HealthChecker:
    """Runs health checks on registered services"""

    def __init__(self, logger: Any = None):
        self._checks: Dict[str, HealthCheckHandler] = {}
        self._results: Dict[str, HealthCheck] = {}
        self._logger = logger

    def register(self, name: str, handler: HealthCheckHandler):
        self._checks[name] = handler
        self._results[name] = HealthCheck(name=name)

    def unregister(self, name: str):
        self._checks.pop(name, None)
        self._results.pop(name, None)

    async def run_checks(self, names: List[str] = None) -> Dict[str, HealthCheck]:
        targets = names if names else list(self._checks.keys())
        tasks = []
        for name in targets:
            if name in self._checks:
                tasks.append(self._run_single(name))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        updated = {}
        for result in results:
            if isinstance(result, HealthCheck):
                self._results[result.name] = result
                updated[result.name] = result
        return updated

    async def run_check(self, name: str) -> HealthCheck:
        if name not in self._checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="No handler registered"
            )
        return await self._run_single(name)

    async def _run_single(self, name: str) -> HealthCheck:
        start = time.time()
        try:
            result = await asyncio.wait_for(self._checks[name](), timeout=10.0)
            if isinstance(result, HealthCheck):
                result.duration_ms = (time.time() - start) * 1000
                result.last_check = time.time()
                return result
            return HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                duration_ms=(time.time() - start) * 1000,
                last_check=time.time(),
            )
        except asyncio.TimeoutError:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out",
                duration_ms=10000,
                last_check=time.time(),
            )
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start) * 1000,
                last_check=time.time(),
            )

    def get_status(self, name: str = None) -> HealthStatus:
        if name:
            result = self._results.get(name)
            return result.status if result else HealthStatus.UNKNOWN
        if not self._results:
            return HealthStatus.UNKNOWN
        statuses = [r.status for r in self._results.values()]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    def get_results(self) -> Dict[str, HealthCheck]:
        return dict(self._results)

    def summary(self) -> Dict[str, Any]:
        results = self.get_results()
        return {
            "overall": self.get_status().value,
            "checks": {
                name: {
                    "status": r.status.value,
                    "message": r.message,
                    "last_check": r.last_check,
                    "duration_ms": r.duration_ms,
                }
                for name, r in results.items()
            },
            "total": len(results),
            "healthy": sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
            "unhealthy": sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY),
            "degraded": sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED),
        }
