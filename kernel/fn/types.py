from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import time
import uuid


class FunctionCategory(Enum):
    SYSTEM_CORE = "system_core"
    INPUT_GATEWAYS = "input_gateways"
    OSINT = "osint"
    SECURITY_SCANNING = "security_scanning"
    OFFENSIVE_ACTIONS = "offensive_actions"
    STORAGE_ANALYTICS = "storage_analytics"
    AI_MCP = "ai_mcp"
    NETWORK_PROXY = "network_proxy"
    TERMUX_MOBILE = "termux_mobile"
    ADVANCED_LOGIC = "advanced_logic"
    SHADOW_BRIDGE = "shadow_bridge"
    CLOUD = "cloud"
    ENTERPRISE = "enterprise"


class FunctionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class FunctionDefinition:
    id: str
    name: str
    description: str
    category: FunctionCategory
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    timeout: float = 30.0
    requires_approval: bool = False
    handler: Optional[Callable] = field(default=None, repr=False)


@dataclass
class FunctionResult:
    function_id: str
    success: bool = False
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    status: FunctionStatus = FunctionStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input: Dict[str, Any] = field(default_factory=dict)
