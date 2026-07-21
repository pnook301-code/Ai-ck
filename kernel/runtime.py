"""
CK-NEXUS Kernel Runtime
Main entry point and lifecycle management
"""
import asyncio
import signal
import sys
import time
import threading
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .config import KernelConfig
from .registry import ServiceRegistry, ServiceDescriptor, ServiceLifetime
from .container import DIContainer
from .events import EventBus
from .commands import CommandBus
from .state import StateManager
from .metrics import MetricsCollector
from .health import HealthChecker
from .logging import StructuredLogger, LogLevel


class KernelState(Enum):
    """Kernel lifecycle states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class KernelRuntime:
    """Main kernel runtime - manages lifecycle and coordinates all services"""
    
    config: 'KernelConfig'
    
    # Core services (initialized in start())
    registry: 'ServiceRegistry' = None
    container: 'DIContainer' = None
    event_bus: 'EventBus' = None
    command_bus: 'CommandBus' = None
    state_manager: 'StateManager' = None
    metrics: 'MetricsCollector' = None
    health_checker: 'HealthChecker' = None
    logger: 'StructuredLogger' = None
    
    # State
    state: 'KernelState' = field(default=KernelState.STOPPED, init=False)
    start_time: float = field(default=0, init=False)
    _shutdown_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _background_tasks: List[asyncio.Task] = field(default_factory=list, init=False)
    _shutdown_callbacks: List[Callable[[], Awaitable[None]]] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        # Setup basic logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured logging"""
        self.logger = StructuredLogger(
            name=self.config.name,
            level=LogLevel.DEBUG if self.config.debug else LogLevel.INFO,
            log_dir=self.config.logs_dir
        )
    
    async def start(self) -> bool:
        """Start the kernel and all services"""
        if self.state != KernelState.STOPPED:
            self.logger.warning(f"Kernel already in state: {self.state.value}")
            return False
        
        self.state = KernelState.STARTING
        self.start_time = time.time()
        self.logger.info("Starting CK-NEXUS Kernel", version="1.0.0")
        
        try:
            # 1. Initialize core services
            await self._initialize_core_services()
            
            # 2. Register core services in registry
            await self._register_core_services()
            
            # 3. Initialize container with core services
            await self._initialize_container()
            
            # 4. Start event processing
            await self._start_event_processing()
            
            # 5. Start background services
            await self._start_background_services()
            
            # 6. Register signal handlers
            self._register_signal_handlers()
            
            # 7. Emit started event
            await self.event_bus.emit("kernel.started", {
                "start_time": self.start_time,
                "config": self.config.to_dict()
            })
            
            self.state = KernelState.RUNNING
            self.logger.info("Kernel started successfully", 
                           startup_time_ms=(time.time() - self.start_time) * 1000)
            return True
            
        except Exception as e:
            self.state = KernelState.ERROR
            self.logger.error("Failed to start kernel", error=str(e), exc_info=True)
            await self._cleanup_on_error()
            raise
    
    async def _initialize_core_services(self):
        """Initialize core infrastructure services"""
        self.logger.debug("Initializing core services")
        
        # Service Registry
        self.registry = ServiceRegistry()
        
        # Event Bus (needs to be first for other services)
        self.event_bus = EventBus(logger=self.logger)
        
        # Command Bus
        self.command_bus = CommandBus(event_bus=self.event_bus, logger=self.logger)
        
        # State Manager
        self.state_manager = StateManager(
            data_dir=self.config.data_dir,
            logger=self.logger
        )
        
        # Metrics Collector
        self.metrics = MetricsCollector(logger=self.logger)
        
        # Health Checker
        self.health_checker = HealthChecker(logger=self.logger)
        
        self.logger.debug("Core services initialized")
    
    async def _register_core_services(self):
        """Register core services in the registry"""
        # Register core services as singletons
        self.registry.register(ServiceDescriptor(
            name="config",
            implementation=lambda: self.config,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="event_bus",
            implementation=lambda: self.event_bus,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="command_bus",
            implementation=lambda: self.command_bus,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="state_manager",
            implementation=lambda: self.state_manager,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="metrics",
            implementation=lambda: self.metrics,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="health_checker",
            implementation=lambda: self.health_checker,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="logger",
            implementation=lambda: self.logger,
            lifetime=ServiceLifetime.SINGLETON
        ))
        
        self.registry.register(ServiceDescriptor(
            name="registry",
            implementation=lambda: self.registry,
            lifetime=ServiceLifetime.SINGLETON
        ))
    
    async def _initialize_container(self):
        """Initialize DI container with registered services"""
        self.container = DIContainer(self.registry, logger=self.logger)
        
        # Register core services in container
        self.container.register_instance("config", self.config)
        self.container.register_instance("event_bus", self.event_bus)
        self.container.register_instance("command_bus", self.command_bus)
        self.container.register_instance("state_manager", self.state_manager)
        self.container.register_instance("metrics", self.metrics)
        self.container.register_instance("health_checker", self.health_checker)
        self.container.register_instance("logger", self.logger)
        self.container.register_instance("kernel", self)
    
    async def _start_event_processing(self):
        """Start event bus processing"""
        await self.event_bus.start()
        self.logger.debug("Event bus started")
    
    async def _start_background_services(self):
        """Start background maintenance tasks"""
        # Metrics collection
        self._background_tasks.append(
            asyncio.create_task(self._metrics_collection_loop())
        )
        
        # Health check loop
        self._background_tasks.append(
            asyncio.create_task(self._health_check_loop())
        )
        
        # State persistence
        self._background_tasks.append(
            asyncio.create_task(self._state_persistence_loop())
        )
        
        self.logger.debug(f"Started {len(self._background_tasks)} background services")
    
    async def _metrics_collection_loop(self):
        """Periodic metrics collection"""
        while self.state == KernelState.RUNNING:
            try:
                await self.metrics.collect_system_metrics()
                await asyncio.sleep(10)  # Every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Metrics collection error", error=str(e))
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """Periodic health checks"""
        while self.state == KernelState.RUNNING:
            try:
                await self.health_checker.run_checks()
                await asyncio.sleep(30)  # Every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Health check error", error=str(e))
                await asyncio.sleep(60)
    
    async def _state_persistence_loop(self):
        """Periodic state persistence"""
        while self.state == KernelState.RUNNING:
            try:
                await self.state_manager.persist()
                await asyncio.sleep(60)  # Every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("State persistence error", error=str(e))
                await asyncio.sleep(120)
    
    def _register_signal_handlers(self):
        """Register OS signal handlers for graceful shutdown"""
        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    signal.signal(sig, self._signal_handler)
                except (ValueError, OSError):
                    pass  # Not available in this context
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating shutdown")
        asyncio.create_task(self.stop())
    
    def on_shutdown(self, callback: Callable[[], Awaitable[None]]):
        """Register a shutdown callback"""
        self._shutdown_callbacks.append(callback)
    
    async def stop(self, timeout: float = None) -> bool:
        """Gracefully stop the kernel"""
        if self.state not in (KernelState.RUNNING, KernelState.STARTING):
            self.logger.warning(f"Kernel not running, current state: {self.state.value}")
            return False
        
        timeout = timeout or self.config.shutdown_timeout
        self.state = KernelState.STOPPING
        self.logger.info("Stopping kernel...")
        
        try:
            # 1. Signal shutdown
            self._shutdown_event.set()
            
            # 2. Run shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    await asyncio.wait_for(callback(), timeout=5.0)
                except Exception as e:
                    self.logger.error("Shutdown callback failed", error=str(e))
            
            # 3. Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # 4. Stop event bus
            await self.event_bus.stop()
            
            # 5. Persist final state
            await self.state_manager.persist()
            
            # 6. Close container
            if self.container:
                await self.container.close()
            
            # 7. Close state manager
            await self.state_manager.close()
            
            self.state = KernelState.STOPPED
            elapsed = time.time() - self.start_time
            self.logger.info("Kernel stopped", uptime_seconds=elapsed)
            return True
            
        except Exception as e:
            self.logger.error("Error during shutdown", error=str(e))
            self.state = KernelState.ERROR
            return False
    
    async def _cleanup_on_error(self):
        """Cleanup on startup error"""
        for task in self._background_tasks:
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        if self.event_bus:
            await self.event_bus.stop()
        if self.container:
            await self.container.close()
        if self.state_manager:
            await self.state_manager.close()
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for kernel lifecycle"""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
    
    def run(self):
        """Run kernel synchronously (blocking)"""
        try:
            asyncio.run(self._run_async())
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
    
    async def _run_async(self):
        """Async run loop"""
        await self.start()
        await self._shutdown_event.wait()
    
    def get_uptime(self) -> float:
        """Get kernel uptime in seconds"""
        if self.start_time > 0:
            return time.time() - self.start_time
        return 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get kernel status"""
        return {
            "state": self.state.value,
            "uptime_seconds": self.get_uptime(),
            "start_time": self.start_time,
            "background_tasks": len(self._background_tasks),
            "registered_services": len(self.registry.services) if self.registry else 0,
        }


@asynccontextmanager
async def create_kernel(config: KernelConfig = None):
    """Create and manage kernel lifecycle"""
    if config is None:
        config = KernelConfig()
    
    kernel = KernelRuntime(config)
    await kernel.start()
    try:
        yield kernel
    finally:
        await kernel.stop()