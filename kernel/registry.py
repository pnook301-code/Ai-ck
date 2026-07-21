"""Service Registry - manages service registration, resolution, and lifetime"""
from typing import Dict, Any, Optional, List, Type, TypeVar
import threading

from .lifetime import ServiceLifetime
from .descriptor import ServiceDescriptor

T = TypeVar('T')


class ServiceRegistry:
    """Central registry for all services with DI support"""

    def __init__(self, logger: Any = None):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._global_scope = "_global_"
        self._logger = logger

    @property
    def services(self) -> Dict[str, ServiceDescriptor]:
        return self._services

    def register(self, descriptor: ServiceDescriptor) -> "ServiceRegistry":
        with self._lock:
            self._services[descriptor.name] = descriptor
            if self._logger:
                self._logger.debug(f"Registered service: {descriptor.name} ({descriptor.lifetime.value})")
        return self

    def register_simple(
        self,
        name: str,
        implementation: Any,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        dependencies: List[str] = None,
        tags: Dict[str, str] = None,
    ) -> "ServiceRegistry":
        return self.register(ServiceDescriptor(
            name=name,
            implementation=implementation,
            lifetime=lifetime,
            dependencies=dependencies or [],
            tags=tags or {},
        ))

    def register_instance(self, name: str, instance: Any, tags: Dict[str, str] = None) -> "ServiceRegistry":
        return self.register(ServiceDescriptor(
            name=name,
            implementation=instance,
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance,
            tags=tags or {},
        ))

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._services:
                del self._services[name]
                return True
            return False

    def resolve(self, name: str, scope: str = None) -> Any:
        with self._lock:
            descriptor = self._services.get(name)
            if not descriptor:
                raise KeyError(f"Service not registered: {name}")

            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if descriptor.instance is None:
                    descriptor.instance = self._create_instance(descriptor)
                return descriptor.instance

            if descriptor.lifetime == ServiceLifetime.SCOPED:
                scope_key = scope or self._global_scope
                if scope_key not in self._scoped_instances:
                    self._scoped_instances[scope_key] = {}
                if name not in self._scoped_instances[scope_key]:
                    self._scoped_instances[scope_key][name] = self._create_instance(descriptor)
                return self._scoped_instances[scope_key][name]

            return self._create_instance(descriptor)

    def resolve_typed(self, service_type: Type[T], scope: str = None) -> Optional[T]:
        with self._lock:
            for name, desc in self._services.items():
                if desc.implementation == service_type:
                    return self.resolve(name, scope)
                if isinstance(desc.implementation, type) and issubclass(desc.implementation, service_type):
                    return self.resolve(name, scope)
            return None

    def resolve_all_with_tag(self, tag_key: str, tag_value: str = None) -> List[Any]:
        results = []
        with self._lock:
            for name, desc in self._services.items():
                value = desc.tags.get(tag_key)
                if value is not None and (tag_value is None or value == tag_value):
                    try:
                        results.append(self.resolve(name))
                    except Exception:
                        continue
        return results

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        if descriptor.instance is not None:
            return descriptor.instance
        if descriptor.factory:
            return descriptor.factory()
        if not descriptor.is_class():
            return descriptor.implementation
        cls = descriptor.implementation
        try:
            return cls()
        except TypeError:
            return cls

    def has_service(self, name: str) -> bool:
        with self._lock:
            return name in self._services

    def get_names(self) -> List[str]:
        with self._lock:
            return list(self._services.keys())

    def clear_scope(self, scope: str):
        with self._lock:
            self._scoped_instances.pop(scope, None)

    def clear_all(self):
        with self._lock:
            self._services.clear()
            self._scoped_instances.clear()
