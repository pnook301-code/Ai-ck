"""Service Registry - Central service registry for dependency injection and service discovery"""
import logging
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from contextvars import ContextVar

from .lifetime import ServiceLifetime
from .descriptor import ServiceDescriptor, create_service_descriptor


T = TypeVar('T')


@dataclass
class ScopeContext:
    """Scope context for scoped services"""
    scope_id: str
    instances: Dict[str, Any] = field(default_factory=dict)


# Context variable for current scope
_current_scope: ContextVar[Optional[str]] = ContextVar('_current_scope', default=None)


class ServiceRegistry:
    """Central service registry for dependency injection and service discovery"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self._services: Dict[str, 'ServiceDescriptor'] = {}
        self._instances: Dict[str, Any] = {}  # Singleton instances
        self._scopes: Dict[str, ScopeContext] = {}
        self._lock = threading.RLock()
        self._logger = logger or logging.getLogger(__name__)
        
        # Register core services
        self._register_core_services()
    
    def _register_core_services(self):
        """Register core framework services"""
        self.register_instance("logger", logging.getLogger("ck-nexus"))
        self.register_instance("service_registry", self)
    
    def register(self, descriptor: 'ServiceDescriptor') -> 'ServiceRegistry':
        """Register a service descriptor"""
        with self._lock:
            if descriptor.name in self._services:
                self._log_warning(f"Overriding service: {descriptor.name}")
            self._services[descriptor.name] = descriptor
            self._log_debug(f"Registered service: {descriptor.name} ({descriptor.lifetime.value})")
        return self
    
    def register_instance(self, name: str, instance: Any, tags: Dict[str, str] = None) -> 'ServiceRegistry':
        """Register an existing instance as singleton"""
        return self.register(ServiceDescriptor(
            name=name,
            implementation=instance,
            lifetime=ServiceLifetime.SINGLETON,
            tags=tags or {}
        ))
    
    def register_factory(self, name: str, factory: Callable, 
                        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
                        dependencies: List[str] = None,
                        tags: Dict[str, str] = None) -> 'ServiceRegistry':
        """Register a factory function"""
        return self.register(ServiceDescriptor(
            name=name,
            implementation=factory,
            lifetime=lifetime,
            dependencies=dependencies or [],
            tags=tags or {},
            factory=True
        ))
    
    def register_class(self, name: str, cls: Type, 
                      lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
                      dependencies: List[str] = None,
                      tags: Dict[str, str] = None) -> 'ServiceRegistry':
        """Register a class for DI"""
        return self.register(ServiceDescriptor(
            name=name,
            implementation=cls,
            lifetime=lifetime,
            dependencies=dependencies or [],
            tags=tags or {}
        ))
    
    def register_singleton(self, name: str, cls: Type = None, instance: Any = None,
                          dependencies: List[str] = None, tags: Dict[str, str] = None) -> 'ServiceRegistry':
        """Register a singleton service"""
        if instance is not None:
            return self.register_instance(name, instance, tags)
        
        if cls is None:
            raise ValueError("Either cls or instance must be provided")
        
        return self.register(ServiceDescriptor(
            name=name,
            implementation=cls,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=dependencies or [],
            tags=tags or {}
        ))
    
    def register_scoped(self, name: str, cls: Type,
                       dependencies: List[str] = None,
                       tags: Dict[str, str] = None) -> 'ServiceRegistry':
        """Register a scoped service"""
        return self.register(ServiceDescriptor(
            name=name,
            implementation=cls,
            lifetime=ServiceLifetime.SCOPED,
            dependencies=dependencies or [],
            tags=tags or {}
        ))
    
    def register_transient(self, name: str, cls: Type,
                          dependencies: List[str] = None,
                          tags: Dict[str, str] = None) -> 'ServiceRegistry':
        """Register a transient service"""
        return self.register(ServiceDescriptor(
            name=name,
            implementation=cls,
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=dependencies or [],
            tags=tags or {}
        ))
    
    def unregister(self, name: str) -> bool:
        """Unregister a service"""
        with self._lock:
            if name in self._services:
                del self._services[name]
                self._instances.pop(name, None)
                return True
        return False
    
    def get(self, name: str) -> Optional['ServiceDescriptor']:
        """Get service descriptor by name"""
        with self._lock:
            return self._services.get(name)
    
    def has(self, name: str) -> bool:
        """Check if service is registered"""
        with self._lock:
            return name in self._services
    
    def get_all(self) -> Dict[str, 'ServiceDescriptor']:
        """Get all registered services"""
        with self._lock:
            return dict(self._services)
    
    def get_by_tag(self, tag_key: str, tag_value: str) -> List['ServiceDescriptor']:
        """Find services by tag"""
        with self._lock:
            return [
                desc for desc in self._services.values()
                if desc.tags.get(tag_key) == tag_value
            ]
    
    def get_by_tag_prefix(self, tag_prefix: str) -> List['ServiceDescriptor']:
        """Find services by tag prefix"""
        with self._lock:
            return [
                desc for desc in self._services.values()
                if any(k.startswith(tag_prefix) for k in desc.tags)
            ]
    
    # Resolution methods
    def resolve(self, name: str) -> Any:
        """Resolve a service by name"""
        descriptor = self.get(name)
        if not descriptor:
            raise KeyError(f"Service not found: {name}")
        return self._create_instance(descriptor)
    
    def resolve_type(self, cls: Type[T]) -> T:
        """Resolve service by type"""
        # Find by type name or implementation
        for desc in self._services.values():
            if desc.implementation == cls or desc.name == cls.__name__:
                return self._create_instance(desc)
        raise KeyError(f"No service registered for type: {cls}")
    
    def _create_instance(self, descriptor: 'ServiceDescriptor') -> Any:
        """Create service instance based on lifetime"""
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._get_or_create_singleton(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._get_or_create_scoped(descriptor)
        else:  # TRANSIENT
            return self._create_new_instance(descriptor)
    
    def _get_or_create_singleton(self, descriptor: 'ServiceDescriptor') -> Any:
        """Get or create singleton instance"""
        with self._lock:
            if descriptor.name in self._instances:
                return self._instances[descriptor.name]
            
            instance = self._create_new_instance(descriptor)
            self._instances[descriptor.name] = instance
            return instance
    
    def _get_or_create_scoped(self, descriptor: 'ServiceDescriptor') -> Any:
        """Get or create scoped instance"""
        scope_id = self.get_current_scope_id()
        if not scope_id:
            raise RuntimeError(f"Scoped service '{descriptor.name}' requires active scope")
        
        scope = self._scopes.get(scope_id)
        if not scope:
            raise RuntimeError(f"Scope {scope_id} not found")
        
        if descriptor.name not in scope.instances:
            scope.instances[descriptor.name] = self._create_new_instance(descriptor)
        return scope.instances[descriptor.name]
    
    def _create_new_instance(self, descriptor: 'ServiceDescriptor') -> Any:
        """Create a new instance of the service"""
        if descriptor.instance is not None:
            return descriptor.instance
        
        if descriptor.factory:
            # Factory function
            return descriptor.factory(self)
        
        if descriptor.is_class():
            # Class instantiation with dependency injection
            return self._instantiate_class(descriptor.implementation, descriptor.dependencies)
        
        # Instance already provided
        return descriptor.implementation
    
    def _instantiate_class(self, cls: Type, dependencies: List[str]) -> Any:
        """Instantiate class with dependency injection"""
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            if param_name in dependencies:
                # Explicit dependency
                kwargs[param_name] = self.resolve(dependencies[param_name])
            elif param.annotation != inspect.Parameter.empty:
                # Type-hinted dependency
                dep_type = param.annotation
                try:
                    kwargs[param_name] = self.resolve_type(dep_type)
                except KeyError:
                    if param.default == inspect.Parameter.empty:
                        raise RuntimeError(f"Cannot resolve dependency: {param_name} ({dep_type})")
            elif param.default != inspect.Parameter.empty:
                # Use default
                pass
            else:
                raise RuntimeError(f"Cannot resolve dependency: {param_name}")
        
        return cls(**kwargs)
    
    def resolve_type(self, cls: Type[T]) -> T:
        """Resolve service by type"""
        return self.resolve_type(cls)
    
    # Scope management
    def begin_scope(self, scope_id: str = None) -> str:
        """Begin a new scope for scoped services"""
        scope_id = scope_id or str(uuid.uuid4())
        with self._lock:
            self._scopes[scope_id] = ScopeContext(scope_id=scope_id)
        return scope_id
    
    def end_scope(self, scope_id: str):
        """End a scope and cleanup scoped instances"""
        with self._lock:
            if scope_id in self._scopes:
                scope = self._scopes[scope_id]
                # Dispose of disposable instances
                for instance in scope.instances.values():
                    if hasattr(instance, 'dispose') and callable(instance.dispose):
                        try:
                            instance.dispose()
                        except Exception:
                            pass
                del self._scopes[scope_id]
    
    @contextmanager
    def scope(self, scope_id: str = None):
        """Context manager for scoped services"""
        scope_id = self.begin_scope(scope_id)
        try:
            yield scope_id
        finally:
            self.end_scope(scope_id)
    
    def get_current_scope_id(self) -> Optional[str]:
        """Get current scope ID"""
        return _current_scope.get()
    
    def set_current_scope(self, scope_id: str):
        """Set current scope"""
        _current_scope.set(scope_id)
    
    # Logging helpers
    def _log_debug(self, msg: str):
        if self._logger:
            self._logger.debug(msg)
    
    def _log_warning(self, msg: str):
        if self._logger:
            self._logger.warning(msg)
    
    def _log_error(self, msg: str):
        if self._logger:
            self._logger.error(msg)
    
    def clear(self):
        """Clear all registrations"""
        with self._lock:
            self._services.clear()
            self._instances.clear()
            self._scopes.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._lock:
            lifetimes = {}
            for desc in self._services.values():
                lifetime = desc.lifetime.value
                lifetimes[lifetime] = lifetimes.get(lifetime, 0) + 1
            
            return {
                "total_services": len(self._services),
                "by_lifetime": lifetimes,
                "singleton_instances": len(self._instances),
                "active_scopes": len(self._scopes),
                "current_scope": self.get_current_scope_id()
            }


# Convenience functions
def create_service_registry(logger: Optional[logging.Logger] = None) -> ServiceRegistry:
    """Create a new service registry"""
    return ServiceRegistry(logger)