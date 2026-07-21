"""
CK-NEXUS Enterprise Kernel - Core Infrastructure
Phase 1: Runtime, Registry, DI Container, Config, State, EventBus, CommandBus
"""
from .runtime import KernelRuntime, KernelConfig
from .registry import ServiceRegistry, ServiceDescriptor, ServiceLifetime
from .container import DIContainer, inject, Inject
from .config import ConfigService, ConfigSource
from .state import StateManager, StateSnapshot
from .events import EventBus, Event, EventHandler
from .commands import CommandBus, Command, CommandHandler
from .metrics import MetricsCollector, MetricType
from .health import HealthCheck, HealthStatus, HealthChecker
from .logging import StructuredLogger, LogLevel

__version__ = "1.0.0"
__all__ = [
    "KernelRuntime",
    "KernelConfig",
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
]