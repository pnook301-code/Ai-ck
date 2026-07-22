"""Shadow Bridge — functions 11.1–11.10

Wraps the 10 core Shadow scripts behind the standard FunctionRegistry interface.
Each handler creates a ShadowBridge instance and delegates execution to the
corresponding script in the Shadow system (local or remote via SSH).
"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc,
        category=FunctionCategory.SHADOW_BRIDGE,
        input_schema=params, handler=handler,
        requires_approval=True,
    )


def _get_bridge(input_data: Dict[str, Any]):
    from ..bridge.shadow_bridge import ShadowBridge
    shadow_home = input_data.get("shadow_home")
    ssh_config = input_data.get("ssh_config")
    if shadow_home and ssh_config:
        return ShadowBridge(shadow_home=shadow_home, ssh_config=ssh_config)
    elif shadow_home:
        return ShadowBridge(shadow_home=shadow_home)
    elif ssh_config:
        return ShadowBridge(ssh_config=ssh_config)
    return ShadowBridge()


async def fn_11_1_nexus_cli(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    cmd = input_data.get("cmd", "")
    return await bridge.execute("nexus_cli", args=[cmd] if cmd else None)


async def fn_11_2_api_key_gen(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    return await bridge.execute("api_key_gen")


async def fn_11_3_unified_controller(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    action = input_data.get("action", "status")
    return await bridge.execute("unified_controller", args=[action])


async def fn_11_4_auto_system(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    mode = input_data.get("mode", "scan")
    return await bridge.execute("auto_system", args=[mode])


async def fn_11_5_vps_auto_reg(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    service = input_data.get("service")
    args = [service] if service else None
    return await bridge.execute("vps_auto_reg", args=args)


async def fn_11_6_web_reg_plugin(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    target_url = input_data.get("target_url")
    args = [target_url] if target_url else None
    return await bridge.execute("web_reg_plugin", args=args)


async def fn_11_7_telegram_gateway(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    action = input_data.get("action", "status")
    return await bridge.execute("telegram_gateway", args=[action])


async def fn_11_8_omni_ai_pool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    query = input_data.get("query")
    args = [query] if query else None
    return await bridge.execute("omni_ai_pool", args=args)


async def fn_11_9_headless_mainframe(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    url = input_data.get("url")
    action = input_data.get("action", "screenshot")
    args = [url, action] if url else [action]
    return await bridge.execute("headless_mainframe", args=args)


async def fn_11_10_smart_router(input_data: Dict[str, Any]) -> Dict[str, Any]:
    bridge = _get_bridge(input_data)
    await bridge.connect()
    query = input_data.get("query")
    args = [query] if query else None
    return await bridge.execute("smart_router", args=args)


definitions = [
    _def("shadow_nexus_cli", "11.1", "Execute Shadow CLI command via bridge",
         fn_11_1_nexus_cli, {
             "cmd": {"type": "string", "required": True},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_api_key_gen", "11.2", "Generate API keys via Shadow system",
         fn_11_2_api_key_gen, {
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_unified_controller", "11.3", "Run unified controller operations",
         fn_11_3_unified_controller, {
             "action": {"type": "string", "default": "status"},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_auto_system", "11.4", "Trigger Shadow automation system",
         fn_11_4_auto_system, {
             "mode": {"type": "string", "default": "scan"},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_vps_auto_reg", "11.5", "VPS auto-registration for services",
         fn_11_5_vps_auto_reg, {
             "service": {"type": "string", "required": True},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_web_reg_plugin", "11.6", "Web registration plugin execution",
         fn_11_6_web_reg_plugin, {
             "target_url": {"type": "string", "required": True},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_telegram_gateway", "11.7", "Telegram gateway operations",
         fn_11_7_telegram_gateway, {
             "action": {"type": "string", "default": "status"},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_omni_ai_pool", "11.8", "Query Omni AI Pool for distributed inference",
         fn_11_8_omni_ai_pool, {
             "query": {"type": "string", "required": True},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_headless_mainframe", "11.9", "Headless browser automation",
         fn_11_9_headless_mainframe, {
             "url": {"type": "string", "required": True},
             "action": {"type": "string", "default": "screenshot"},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
    _def("shadow_smart_router", "11.10", "Smart routing for Shadow requests",
         fn_11_10_smart_router, {
             "query": {"type": "string", "required": True},
             "shadow_home": {"type": "string", "default": ""},
             "ssh_config": {"type": "object", "default": {}},
         }),
]


def register_shadow_bridge(registry):
    for fn in definitions:
        registry.register(fn)
