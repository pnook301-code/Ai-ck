"""Service Descriptor - defines a service in the registry"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
import inspect

from .lifetime import ServiceLifetime


@dataclass
class ServiceDescriptor:
    """Describes a service in the registry"""
    name: str
    implementation: Any  # Class, factory function, or instance
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    dependencies: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    factory: Optional[Callable] = field(default=None, repr=False)
    instance: Any = field(default=None, repr=False)
    
    def __post_init__(self):
        # Auto-detect factory if callable but not a class
        if self.factory is None and callable(self.implementation):
            if not inspect.isclass(self.implementation):
                self.factory = self.implementation
    
    def is_class(self) -> bool:
        """Check if implementation is a class"""
        return inspect.isclass(self.implementation)
    
    def is_factory(self) -> bool:
        """Check if implementation is a factory function"""
        return self.factory is not None
    
    def is_instance(self) -> bool:
        """Check if implementation is a pre-created instance"""
        return not callable(self.implementation) or (self.instance is not None)


def create_service_descriptor(
    name: str,
    implementation: Any,
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    dependencies: List[str] = None,
    tags: Dict[str, str] = None
) -> 'ServiceDescriptor':
    """Factory function to create service descriptor"""
    return ServiceDescriptor(
        name=name,
        implementation=implementation,
        lifetime=lifetime,
        dependencies=dependencies or [],
        tags=tags or {}
    )