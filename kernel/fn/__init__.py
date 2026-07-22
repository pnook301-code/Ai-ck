"""Function Registry - 110 auto-functions for CK-NEXUS AIOS"""
from .types import FunctionDefinition, FunctionResult, FunctionCategory, FunctionStatus
from .registry import FunctionRegistry

__all__ = [
    "FunctionDefinition",
    "FunctionResult",
    "FunctionCategory",
    "FunctionStatus",
    "FunctionRegistry",
]


def register_all_categories(registry: FunctionRegistry) -> int:
    from .category1 import register_system_core
    from .category2 import register_input_gateways
    from .category3 import register_osint
    from .category4 import register_security_scanning
    from .category5 import register_offensive
    from .category6 import register_storage_analytics
    from .category7 import register_ai_mcp
    from .category8 import register_network_proxy
    from .category9 import register_termux_mobile
    from .category10 import register_advanced_logic
    from .category11 import register_shadow_bridge
    from .category12 import register_cloud
    from .category13 import register_enterprise
    from .category15 import register_kubernetes

    count_before = len(registry._functions)
    register_system_core(registry)
    register_input_gateways(registry)
    register_osint(registry)
    register_security_scanning(registry)
    register_offensive(registry)
    register_storage_analytics(registry)
    register_ai_mcp(registry)
    register_network_proxy(registry)
    register_termux_mobile(registry)
    register_advanced_logic(registry)
    register_shadow_bridge(registry)
    register_cloud(registry)
    register_enterprise(registry)
    register_kubernetes(registry)
    return len(registry._functions) - count_before
