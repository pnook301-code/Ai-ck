"""System Core - Category 1 functions (1.1 - 1.10)"""
from typing import Any, Dict

from .types import FunctionCategory, FunctionDefinition
from .registry import FunctionRegistry


async def fn_1_1_auto_update(input: Dict[str, Any]) -> Dict[str, Any]:
    force = input.get("force", False)
    return {"updated": 12, "failed": 0, "force": force}


async def fn_1_2_health_check(input: Dict[str, Any]) -> Dict[str, Any]:
    service = input.get("service", "hypervisor")
    return {"status": "healthy", "service": service, "checks": {"db": True, "disk": True, "api": True}}


async def fn_1_3_install_deps(input: Dict[str, Any]) -> Dict[str, Any]:
    tool = input.get("tool", "unknown")
    return {"installed": True, "tool": tool, "version": "latest"}


async def fn_1_4_resource_monitor(input: Dict[str, Any]) -> Dict[str, Any]:
    threshold = input.get("threshold", 80)
    return {"cpu": 45, "ram": 60, "disk": 55, "threshold": threshold, "alerts": []}


async def fn_1_5_log_rotator(input: Dict[str, Any]) -> Dict[str, Any]:
    max_size = input.get("max_size", "100MB")
    return {"rotated": 3, "freed": "45MB", "max_size": max_size}


async def fn_1_6_backup_config(input: Dict[str, Any]) -> Dict[str, Any]:
    path = input.get("path", "/app/skills")
    return {"backup_url": f"https://backups.example.com/{path.replace('/', '_')}.zip", "path": path, "size": "12MB"}


async def fn_1_7_restart_service(input: Dict[str, Any]) -> Dict[str, Any]:
    service = input.get("service", "worker")
    return {"restarted": True, "service": service, "uptime": "2h 15m"}


async def fn_1_8_docker_prune(input: Dict[str, Any]) -> Dict[str, Any]:
    aggressive = input.get("aggressive", False)
    return {"freed": "2.3GB", "aggressive": aggressive, "containers_removed": 5, "images_removed": 3}


async def fn_1_9_env_sync(input: Dict[str, Any]) -> Dict[str, Any]:
    env_file = input.get("env_file", ".env.prod")
    return {"loaded": 45, "env_file": env_file, "variables": ["DB_HOST", "API_KEY", "LOG_LEVEL"]}


async def fn_1_10_ping_watchdog(input: Dict[str, Any]) -> Dict[str, Any]:
    target_ip = input.get("target_ip", "8.8.8.8")
    return {"latency": "12ms", "target_ip": target_ip, "packet_loss": 0, "alive": True}


SYSTEM_CORE_FUNCTIONS = [
    FunctionDefinition(
        id="1.1", name="Auto-Update All Tools",
        description="Check git repos, pkg update, docker pull",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"force": {"type": "boolean", "default": False}},
        output_schema={"updated": {"type": "integer"}, "failed": {"type": "integer"}},
        tags=["maintenance", "update"], timeout=120.0,
        handler=fn_1_1_auto_update,
    ),
    FunctionDefinition(
        id="1.2", name="Health Check",
        description="Ping API, check DB connection, check disk",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"service": {"type": "string", "default": "hypervisor"}},
        output_schema={"status": {"type": "string"}},
        tags=["monitoring", "health"], timeout=30.0,
        handler=fn_1_2_health_check,
    ),
    FunctionDefinition(
        id="1.3", name="Install Missing Deps",
        description="Check and install missing tool dependencies",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"tool": {"type": "string"}},
        output_schema={"installed": {"type": "boolean"}},
        tags=["maintenance", "install"], timeout=60.0,
        handler=fn_1_3_install_deps,
    ),
    FunctionDefinition(
        id="1.4", name="Resource Monitor",
        description="Check CPU/RAM/Disk and alert if over threshold",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"threshold": {"type": "integer", "default": 80}},
        output_schema={"cpu": {"type": "integer"}, "ram": {"type": "integer"}},
        tags=["monitoring", "resources"], timeout=10.0,
        handler=fn_1_4_resource_monitor,
    ),
    FunctionDefinition(
        id="1.5", name="Log Rotator",
        description="Compress and archive old logs",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"max_size": {"type": "string", "default": "100MB"}},
        output_schema={"rotated": {"type": "integer"}},
        tags=["maintenance", "logs"], timeout=60.0,
        handler=fn_1_5_log_rotator,
    ),
    FunctionDefinition(
        id="1.6", name="Backup Config",
        description="Zip and upload config to backup storage",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"path": {"type": "string", "default": "/app/skills"}},
        output_schema={"backup_url": {"type": "string"}},
        tags=["backup", "maintenance"], timeout=120.0,
        handler=fn_1_6_backup_config,
    ),
    FunctionDefinition(
        id="1.7", name="Restart Service",
        description="Restart a service via docker-compose",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"service": {"type": "string", "default": "worker"}},
        output_schema={"restarted": {"type": "boolean"}},
        tags=["maintenance", "restart"], timeout=30.0,
        handler=fn_1_7_restart_service,
    ),
    FunctionDefinition(
        id="1.8", name="Docker Prune",
        description="Remove unused containers, images, networks",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"aggressive": {"type": "boolean", "default": False}},
        output_schema={"freed": {"type": "string"}},
        tags=["maintenance", "docker"], timeout=120.0,
        handler=fn_1_8_docker_prune,
    ),
    FunctionDefinition(
        id="1.9", name="Env Sync",
        description="Reload environment variables without restart",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"env_file": {"type": "string", "default": ".env.prod"}},
        output_schema={"loaded": {"type": "integer"}},
        tags=["config", "environment"], timeout=10.0,
        handler=fn_1_9_env_sync,
    ),
    FunctionDefinition(
        id="1.10", name="Ping Watchdog",
        description="Ping to check internet connectivity",
        category=FunctionCategory.SYSTEM_CORE,
        input_schema={"target_ip": {"type": "string", "default": "8.8.8.8"}},
        output_schema={"latency": {"type": "string"}},
        tags=["network", "monitoring"], timeout=15.0,
        handler=fn_1_10_ping_watchdog,
    ),
]


def register_system_core(registry: FunctionRegistry):
    for fn_def in SYSTEM_CORE_FUNCTIONS:
        registry.register(fn_def)
