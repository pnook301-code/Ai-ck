"""Dependency Injection Container"""
from typing import Any, Dict, Optional, Callable, TypeVar, Type
import threading
import inspect

T = TypeVar('T')


class DIContainer:
    """DI Container wrapping ServiceRegistry"""

    def __init__(self, registry: Any = None, logger: Any = None):
        self._registry = registry
        self._logger = logger
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    def register(self, name: str, implementation: Any):
        with self._lock:
            self._factories[name] = implementation

    def register_instance(self, name: str, instance: Any):
        with self._lock:
            self._instances[name] = instance

    def register_factory(self, name: str, factory: Callable):
        with self._lock:
            self._factories[name] = factory

    def resolve(self, name: str) -> Any:
        with self._lock:
            if name in self._instances:
                return self._instances[name]
            if name in self._factories:
                factory = self._factories[name]
                instance = factory() if not inspect.isclass(factory) else factory()
                self._instances[name] = instance
                return instance
            if self._registry:
                return self._registry.resolve(name)
            raise KeyError(f"Cannot resolve: {name}")

    def resolve_typed(self, service_type: Type[T]) -> Optional[T]:
        if self._registry:
            return self._registry.resolve_typed(service_type)
        return None

    def has(self, name: str) -> bool:
        return name in self._instances or name in self._factories or bool(
            self._registry and self._registry.has_service(name))

    async def close(self):
        with self._lock:
            self._instances.clear()
            self._factories.clear()


class Inject:
    """Descriptor-based injection marker"""

    def __init__(self, name: str = None):
        self.name = name


def inject(container: DIContainer = None):
    """Decorator that injects dependencies from container"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            effective_container = container or getattr(func, '_container', None)
            if not effective_container:
                return func(*args, **kwargs)
            sig = inspect.signature(func)
            for name, param in sig.parameters.items():
                if name not in kwargs:
                    try:
                        kwargs[name] = effective_container.resolve(name)
                    except KeyError:
                        pass
            return func(*args, **kwargs)
        wrapper._container = container
        return wrapper
    return decorator
