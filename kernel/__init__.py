"""
CK-NEXUS Enterprise Kernel - Core Runtime
"""
from .runtime import KernelRuntime, KernelConfig, KernelState
from .registry import ServiceRegistry, ServiceDescriptor, ServiceLifetime
from .container import DIContainer, inject, Inject
from .config import ConfigService, ConfigSource
from .state import StateManager, StateSnapshot
from .events import EventBus, Event, EventHandler
from .commands import CommandBus, Command, CommandHandler
from .metrics import MetricsCollector, MetricType
from .health import HealthCheck, HealthStatus, HealthChecker
from .logger import StructuredLogger, LogLevel
from .cache import CacheService, CacheBackend
from .lifecycle import LifecycleManager, LifecyclePhase
from .scheduler import TaskScheduler, ScheduledTask
from .security import SecurityService, AuthProvider, AuthorizationPolicy
from .bootstrap import BootstrapService

__version__ = "1.0.0"
__all__ = [
    "KernelRuntime",
    "KernelConfig",
    "KernelState",
    "ServiceRegistry",
    "ServiceDescriptor",
    "ServiceLifetime",
    "DIContainer",
    "inject",
    "Inject",
    "ConfigService",
    "ConfigSource",
    "StateManager",
    "StateSnapshot",
    "EventBus",
    "Event",
    "EventHandler",
    "CommandBus",
    "Command",
    "CommandHandler",
    "MetricsCollector",
    "MetricType",
    "HealthCheck",
    "HealthStatus",
    "HealthChecker",
    "StructuredLogger",
    "LogLevel",
    "CacheService",
    "CacheBackend",
    "LifecycleManager",
    "LifecyclePhase",
    "TaskScheduler",
    "ScheduledTask",
    "SecurityService",
    "AuthProvider",
    "AuthorizationPolicy",
    "BootstrapService",
]