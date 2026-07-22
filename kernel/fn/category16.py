"""Category 16 — Billing Functions (16.1–16.10)."""
from typing import Any, Dict

_billing_mgr = None
_audit_log = None


def _get_billing():
    global _billing_mgr
    if _billing_mgr is None:
        from kernel.enterprise.billing import BillingManager
        _billing_mgr = BillingManager()
    return _billing_mgr


def _get_audit():
    global _audit_log
    if _audit_log is None:
        from kernel.enterprise.audit import AuditLogger
        _audit_log = AuditLogger()
    return _audit_log


async def fn_16_1_create_customer(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.billing import BillingPlan
    from kernel.enterprise.audit import AuditAction
    customer = _get_billing().create_customer(input_data.get("tenant_id", ""), input_data.get("email", ""), input_data.get("name", ""), BillingPlan(input_data.get("plan", "free")), input_data.get("metadata"))
    _get_audit().log(AuditAction.API_CALL, details={"action": "billing.create_customer", "customer_id": customer.id})
    return {"customer": customer.to_dict()}


async def fn_16_2_create_subscription(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.billing import BillingPlan
    from kernel.enterprise.audit import AuditAction
    sub = _get_billing().create_subscription(input_data.get("customer_id", ""), BillingPlan(input_data.get("plan", "starter")), input_data.get("billing_cycle", "monthly"))
    if not sub:
        return {"error": "Customer not found"}
    _get_audit().log(AuditAction.API_CALL, details={"action": "billing.create_subscription", "subscription_id": sub.id})
    return {"subscription": sub.to_dict()}


async def fn_16_3_create_invoice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.audit import AuditAction
    invoice = _get_billing().create_invoice(input_data.get("customer_id", ""), input_data.get("amount", 0), input_data.get("currency", "USD"), input_data.get("description", ""), input_data.get("subscription_id"))
    if not invoice:
        return {"error": "Customer not found"}
    _get_audit().log(AuditAction.API_CALL, details={"action": "billing.create_invoice", "invoice_id": invoice.id})
    return {"invoice": invoice.to_dict()}


async def fn_16_4_pay_invoice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.audit import AuditAction
    invoice = _get_billing().pay_invoice(input_data.get("invoice_id", ""))
    if not invoice:
        return {"error": "Invoice not found or not payable"}
    _get_audit().log(AuditAction.API_CALL, details={"action": "billing.pay_invoice", "invoice_id": invoice.id})
    return {"invoice": invoice.to_dict()}


async def fn_16_5_cancel_subscription(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.audit import AuditAction
    sub = _get_billing().cancel_subscription(input_data.get("subscription_id", ""))
    if not sub:
        return {"error": "Subscription not found or already cancelled"}
    _get_audit().log(AuditAction.API_CALL, details={"action": "billing.cancel_subscription", "subscription_id": sub.id})
    return {"subscription": sub.to_dict()}


async def fn_16_6_list_invoices(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.billing import InvoiceStatus
    status = InvoiceStatus(input_data["status"]) if input_data.get("status") else None
    invoices = _get_billing().list_invoices(customer_id=input_data.get("customer_id"), status=status, limit=input_data.get("limit", 100))
    return {"invoices": [i.to_dict() for i in invoices], "count": len(invoices)}


async def fn_16_7_get_usage(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _get_billing().get_usage(input_data.get("customer_id", ""))


async def fn_16_8_revenue_stats(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _get_billing().get_revenue_stats()


async def fn_16_9_upgrade_plan(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.enterprise.billing import BillingPlan
    from kernel.enterprise.audit import AuditAction
    tenant_id = input_data.get("tenant_id", "")
    new_plan = BillingPlan(input_data.get("plan", "starter"))
    customer = _get_billing().get_customer_by_tenant(tenant_id)
    if not customer:
        return {"error": "No customer found for tenant"}
    for s in _get_billing().list_subscriptions(customer_id=customer.id):
        if s.status.value == "active":
            _get_billing().cancel_subscription(s.id)
            break
    new_sub = _get_billing().create_subscription(customer.id, new_plan)
    _get_audit().log(AuditAction.API_CALL, details={"action": "billing.upgrade_plan", "tenant_id": tenant_id})
    return {"customer": customer.to_dict(), "subscription": new_sub.to_dict() if new_sub else None, "upgraded": True}


async def fn_16_10_billing_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {"billing": _get_billing().get_revenue_stats(), "plans": _get_billing().get_plan_info()}


def _def(name, fn_id, desc, handler, params):
    from kernel.fn.types import FunctionDefinition, FunctionCategory
    return FunctionDefinition(id=fn_id, name=name, description=desc, category=FunctionCategory.BILLING, handler=handler, input_schema=params)


def register_billing(registry):
    fns = [
        _def("billing_create_customer", "16.1", "Create billing customer", fn_16_1_create_customer, {"tenant_id": {"type": "string", "required": True}, "email": {"type": "string", "required": True}, "name": {"type": "string", "required": True}, "plan": {"type": "string", "default": "free"}}),
        _def("billing_create_subscription", "16.2", "Create subscription plan", fn_16_2_create_subscription, {"customer_id": {"type": "string", "required": True}, "plan": {"type": "string", "default": "starter"}, "billing_cycle": {"type": "string", "default": "monthly"}}),
        _def("billing_create_invoice", "16.3", "Create invoice for customer", fn_16_3_create_invoice, {"customer_id": {"type": "string", "required": True}, "amount": {"type": "integer", "required": True}, "currency": {"type": "string", "default": "USD"}, "description": {"type": "string", "default": ""}}),
        _def("billing_pay_invoice", "16.4", "Mark invoice as paid", fn_16_4_pay_invoice, {"invoice_id": {"type": "string", "required": True}}),
        _def("billing_cancel_subscription", "16.5", "Cancel active subscription", fn_16_5_cancel_subscription, {"subscription_id": {"type": "string", "required": True}}),
        _def("billing_list_invoices", "16.6", "List invoices with filters", fn_16_6_list_invoices, {"customer_id": {"type": "string", "default": ""}, "status": {"type": "string", "default": ""}, "limit": {"type": "integer", "default": 100}}),
        _def("billing_get_usage", "16.7", "Get customer usage and limits", fn_16_7_get_usage, {"customer_id": {"type": "string", "required": True}}),
        _def("billing_revenue_stats", "16.8", "Get platform revenue statistics", fn_16_8_revenue_stats, {}),
        _def("billing_upgrade_plan", "16.9", "Upgrade tenant billing plan", fn_16_9_upgrade_plan, {"tenant_id": {"type": "string", "required": True}, "plan": {"type": "string", "required": True}}),
        _def("billing_status", "16.10", "Billing module status", fn_16_10_billing_status, {}),
    ]
    for fn in fns:
        registry.register(fn)
    return len(fns)
