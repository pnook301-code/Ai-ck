"""Immutable audit trail — log every action with full context."""
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditAction(Enum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"
    TENANT_DELETE = "tenant.delete"
    FUNCTION_EXECUTE = "function.execute"
    AGENT_START = "agent.start"
    AGENT_STOP = "agent.stop"
    LICENSE_CREATE = "license.create"
    LICENSE_VALIDATE = "license.validate"
    LICENSE_REVOKE = "license.revoke"
    CONFIG_CHANGE = "config.change"
    API_CALL = "api.call"
    ERROR = "error"


class AuditSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    id: str
    timestamp: float
    action: AuditAction
    severity: AuditSeverity
    tenant_id: Optional[str]
    user_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "timestamp": self.timestamp,
            "action": self.action.value, "severity": self.severity.value,
            "tenant_id": self.tenant_id, "user_id": self.user_id,
            "resource_type": self.resource_type, "resource_id": self.resource_id,
            "details": self.details, "ip_address": self.ip_address,
            "user_agent": self.user_agent, "success": self.success,
        }


class AuditLogger:
    def __init__(self, max_events: int = 100000):
        self._events: List[AuditEvent] = []
        self._max_events = max_events

    def log(self, action: AuditAction, severity: AuditSeverity = AuditSeverity.INFO,
            tenant_id: Optional[str] = None, user_id: Optional[str] = None,
            resource_type: Optional[str] = None, resource_id: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None,
            user_agent: Optional[str] = None, success: bool = True) -> AuditEvent:
        event = AuditEvent(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            timestamp=time.time(),
            action=action, severity=severity,
            tenant_id=tenant_id, user_id=user_id,
            resource_type=resource_type, resource_id=resource_id,
            details=details or {}, ip_address=ip_address,
            user_agent=user_agent, success=success,
        )
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        return event

    def query(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None,
              action: Optional[AuditAction] = None, severity: Optional[AuditSeverity] = None,
              since: Optional[float] = None, limit: int = 100) -> List[AuditEvent]:
        results = self._events
        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if severity:
            results = [e for e in results if e.severity == severity]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        for e in self._events:
            if e.id == event_id:
                return e
        return None

    def get_stats(self) -> Dict[str, Any]:
        events = self._events
        return {
            "total_events": len(events),
            "by_action": {a.value: len([e for e in events if e.action == a]) for a in AuditAction},
            "by_severity": {s.value: len([e for e in events if e.severity == s]) for s in AuditSeverity},
            "error_count": len([e for e in events if not e.success]),
            "oldest": events[0].timestamp if events else None,
            "newest": events[-1].timestamp if events else None,
        }

    def export_events(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._events[-limit:]]
