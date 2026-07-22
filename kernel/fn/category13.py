"""Category 13 — Enterprise Functions (13.1–13.10)."""
import time
from typing import Any, Dict

_tenant_mgr = None
_audit_log = None
_license_mgr = None


def _get_tenant():
    global _tenant_mgr
    if _tenant_mgr is None:
        from kernel.enterprise.tenant import TenantManager
        _tenant_mgr = TenantManager()
    return _tenant_mgr


def _get_audit():
    global _audit_log
    if _audit_log is None:
        from kernel.enterprise.audit import AuditLogger
        _audit_log = AuditLogger()
    return _audit_log


def _get_license():
    global _license_mgr
    if _license_mgr is None:
        from kernel.enterprise.license import LicenseManager
        _license_mgr = LicenseManager()
    return _license_mgr


async def fn_13_1_create_tenant(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.tenant import TenantPlan
    name = input_data.get("name", "unnamed")
    plan = TenantPlan(input_data.get("plan", "free"))
    tenant = _get_tenant().create_tenant(name, plan, input_data.get("metadata"))
    from kernel.enterprise.audit import AuditAction
    _get_audit().log(AuditAction.TENANT_CREATE, details={"tenant_id": tenant.id, "name": name})
    return {"tenant": tenant.to_dict()}


async def fn_13_2_list_tenants(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.tenant import TenantStatus
    status = None
    if s := input_data.get("status"):
        status = TenantStatus(s)
    tenants = _get_tenant().list_tenants(status)
    return {"tenants": [t.to_dict() for t in tenants], "count": len(tenants)}


async def fn_13_3_delete_tenant(input_data: Dict[str, Any]) -> Dict[str, Any]:
    tid = input_data.get("tenant_id", "")
    ok = _get_tenant().delete_tenant(tid)
    if ok:
        from kernel.enterprise.audit import AuditAction
        _get_audit().log(AuditAction.TENANT_DELETE, details={"tenant_id": tid})
    return {"success": ok, "tenant_id": tid}


async def fn_13_4_audit_log(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.audit import AuditAction, AuditSeverity
    action = AuditAction(input_data.get("action", "api.call"))
    severity = AuditSeverity(input_data.get("severity", "info"))
    event = _get_audit().log(
        action=action, severity=severity,
        tenant_id=input_data.get("tenant_id"),
        user_id=input_data.get("user_id"),
        resource_type=input_data.get("resource_type"),
        resource_id=input_data.get("resource_id"),
        details=input_data.get("details", {}),
    )
    return {"event": event.to_dict()}


async def fn_13_5_audit_query(input_data: Dict[str, Any]) -> Dict[str, Any]:
    events = _get_audit().query(
        tenant_id=input_data.get("tenant_id"),
        user_id=input_data.get("user_id"),
        limit=input_data.get("limit", 100),
    )
    return {"events": [e.to_dict() for e in events], "count": len(events)}


async def fn_13_6_generate_license(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.license import LicenseTier
    tenant_id = input_data.get("tenant_id", "")
    tier = LicenseTier(input_data.get("tier", "trial"))
    duration = input_data.get("duration_days")
    lic = _get_license().generate_license(tenant_id, tier, duration)
    from kernel.enterprise.audit import AuditAction
    _get_audit().log(AuditAction.LICENSE_CREATE, details={"license_id": lic.id, "tenant_id": tenant_id})
    return {"license": lic.to_dict()}


async def fn_13_7_validate_license(input_data: Dict[str, Any]) -> Dict[str, Any]:
    key = input_data.get("key", "")
    result = _get_license().validate_license(key)
    from kernel.enterprise.audit import AuditAction
    _get_audit().log(AuditAction.LICENSE_VALIDATE, details={"key_preview": key[:12] + "..." if len(key) > 12 else key, "valid": result.get("valid")})
    return result


async def fn_13_8_revoke_license(input_data: Dict[str, Any]) -> Dict[str, Any]:
    key = input_data.get("key", "")
    ok = _get_license().revoke_license(key)
    if ok:
        from kernel.enterprise.audit import AuditAction
        _get_audit().log(AuditAction.LICENSE_REVOKE, details={"key_preview": key[:12] + "..." if len(key) > 12 else key})
    return {"success": ok}


async def fn_13_9_license_info(input_data: Dict[str, Any]) -> Dict[str, Any]:
    key = input_data.get("key", "")
    lic = _get_license().get_license(key)
    if not lic:
        return {"error": "License not found"}
    return {"license": lic.to_dict()}


async def fn_13_10_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tenants": _get_tenant().get_stats(),
        "audit": _get_audit().get_stats(),
        "licenses": _get_license().get_stats(),
    }


def _def(name, fn_id, desc, handler, params):
    from kernel.fn.types import FunctionDefinition, FunctionCategory
    return FunctionDefinition(
        id=fn_id, name=name, description=desc,
        category=FunctionCategory.ENTERPRISE,
        handler=handler, input_schema=params,
    )


def register_enterprise(registry):
    fns = [
        _def("enterprise_create_tenant", "13.1", "Create a new tenant",
             fn_13_1_create_tenant, {
                 "name": {"type": "string", "required": True},
                 "plan": {"type": "string", "default": "free"},
                 "metadata": {"type": "object", "default": {}},
             }),
        _def("enterprise_list_tenants", "13.2", "List all tenants",
             fn_13_2_list_tenants, {
                 "status": {"type": "string", "default": ""},
             }),
        _def("enterprise_delete_tenant", "13.3", "Delete a tenant",
             fn_13_3_delete_tenant, {
                 "tenant_id": {"type": "string", "required": True},
             }),
        _def("enterprise_audit_log", "13.4", "Create audit log entry",
             fn_13_4_audit_log, {
                 "action": {"type": "string", "required": True},
                 "severity": {"type": "string", "default": "info"},
                 "tenant_id": {"type": "string", "default": ""},
                 "user_id": {"type": "string", "default": ""},
                 "resource_type": {"type": "string", "default": ""},
                 "resource_id": {"type": "string", "default": ""},
                 "details": {"type": "object", "default": {}},
             }),
        _def("enterprise_audit_query", "13.5", "Query audit logs",
             fn_13_5_audit_query, {
                 "tenant_id": {"type": "string", "default": ""},
                 "user_id": {"type": "string", "default": ""},
                 "limit": {"type": "integer", "default": 100},
             }),
        _def("enterprise_generate_license", "13.6", "Generate license key",
             fn_13_6_generate_license, {
                 "tenant_id": {"type": "string", "required": True},
                 "tier": {"type": "string", "default": "trial"},
                 "duration_days": {"type": "integer", "default": 30},
             }),
        _def("enterprise_validate_license", "13.7", "Validate license key",
             fn_13_7_validate_license, {
                 "key": {"type": "string", "required": True},
             }),
        _def("enterprise_revoke_license", "13.8", "Revoke license key",
             fn_13_8_revoke_license, {
                 "key": {"type": "string", "required": True},
             }),
        _def("enterprise_license_info", "13.9", "Get license information",
             fn_13_9_license_info, {
                 "key": {"type": "string", "required": True},
             }),
        _def("enterprise_status", "13.10", "Enterprise module status",
             fn_13_10_status, {}),
    ]
    for fn in fns:
        registry.register(fn)
    return len(fns)
