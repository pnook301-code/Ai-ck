"""Billing system — plans, pricing, invoices, subscriptions."""
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BillingPlan(Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class InvoiceStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class SubscriptionStatus(Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trailing"


PLAN_PRICING = {
    BillingPlan.FREE: {"monthly": 0, "annual": 0, "currency": "USD"},
    BillingPlan.STARTER: {"monthly": 49, "annual": 470, "currency": "USD"},
    BillingPlan.PROFESSIONAL: {"monthly": 199, "annual": 1910, "currency": "USD"},
    BillingPlan.ENTERPRISE: {"monthly": 0, "annual": 0, "currency": "USD", "note": "Custom pricing"},
}

PLAN_LIMITS = {
    BillingPlan.FREE: {"max_users": 5, "max_api_calls": 10000, "max_storage_mb": 100, "max_agents": 2, "support_level": "community"},
    BillingPlan.STARTER: {"max_users": 20, "max_api_calls": 100000, "max_storage_mb": 1000, "max_agents": 10, "support_level": "email"},
    BillingPlan.PROFESSIONAL: {"max_users": 100, "max_api_calls": 1000000, "max_storage_mb": 10000, "max_agents": 50, "support_level": "priority"},
    BillingPlan.ENTERPRISE: {"max_users": -1, "max_api_calls": -1, "max_storage_mb": -1, "max_agents": -1, "support_level": "dedicated"},
}


@dataclass
class Customer:
    id: str
    tenant_id: str
    email: str
    name: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    plan: BillingPlan = BillingPlan.FREE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "tenant_id": self.tenant_id, "email": self.email, "name": self.name, "created_at": self.created_at, "updated_at": self.updated_at, "plan": self.plan.value, "metadata": self.metadata}


@dataclass
class Subscription:
    id: str
    customer_id: str
    plan: BillingPlan
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    billing_cycle: str = "monthly"
    started_at: float = field(default_factory=time.time)
    current_period_start: float = field(default_factory=time.time)
    current_period_end: float = 0.0
    cancelled_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "customer_id": self.customer_id, "plan": self.plan.value, "status": self.status.value, "billing_cycle": self.billing_cycle, "started_at": self.started_at, "current_period_start": self.current_period_start, "current_period_end": self.current_period_end, "cancelled_at": self.cancelled_at, "metadata": self.metadata}


@dataclass
class Invoice:
    id: str
    customer_id: str
    subscription_id: Optional[str]
    amount: int
    currency: str
    status: InvoiceStatus = InvoiceStatus.PENDING
    description: str = ""
    created_at: float = field(default_factory=time.time)
    paid_at: Optional[float] = None
    due_at: Optional[float] = None
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "customer_id": self.customer_id, "subscription_id": self.subscription_id, "amount": self.amount, "currency": self.currency, "status": self.status.value, "description": self.description, "created_at": self.created_at, "paid_at": self.paid_at, "due_at": self.due_at, "line_items": self.line_items, "metadata": self.metadata}


class BillingManager:
    def __init__(self):
        self._customers: Dict[str, Customer] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._invoices: Dict[str, Invoice] = {}

    def create_customer(self, tenant_id: str, email: str, name: str, plan: BillingPlan = BillingPlan.FREE, metadata: Optional[Dict[str, Any]] = None) -> Customer:
        cid = f"cust_{uuid.uuid4().hex[:12]}"
        customer = Customer(id=cid, tenant_id=tenant_id, email=email, name=name, plan=plan, metadata=metadata or {})
        self._customers[cid] = customer
        return customer

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self._customers.get(customer_id)

    def get_customer_by_tenant(self, tenant_id: str) -> Optional[Customer]:
        for c in self._customers.values():
            if c.tenant_id == tenant_id:
                return c
        return None

    def list_customers(self, plan: Optional[BillingPlan] = None) -> List[Customer]:
        customers = list(self._customers.values())
        if plan:
            customers = [c for c in customers if c.plan == plan]
        return customers

    def create_subscription(self, customer_id: str, plan: BillingPlan, billing_cycle: str = "monthly", metadata: Optional[Dict[str, Any]] = None) -> Optional[Subscription]:
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        period_seconds = 30 * 86400 if billing_cycle == "monthly" else 365 * 86400
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        now = time.time()
        subscription = Subscription(id=sub_id, customer_id=customer_id, plan=plan, billing_cycle=billing_cycle, current_period_start=now, current_period_end=now + period_seconds, metadata=metadata or {})
        self._subscriptions[sub_id] = subscription
        customer.plan = plan
        customer.updated_at = now
        return subscription

    def cancel_subscription(self, subscription_id: str) -> Optional[Subscription]:
        sub = self._subscriptions.get(subscription_id)
        if not sub or sub.status == SubscriptionStatus.CANCELLED:
            return None
        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = time.time()
        return sub

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        return self._subscriptions.get(subscription_id)

    def list_subscriptions(self, customer_id: Optional[str] = None, status: Optional[SubscriptionStatus] = None) -> List[Subscription]:
        subs = list(self._subscriptions.values())
        if customer_id:
            subs = [s for s in subs if s.customer_id == customer_id]
        if status:
            subs = [s for s in subs if s.status == status]
        return subs

    def create_invoice(self, customer_id: str, amount: int, currency: str = "USD", description: str = "", subscription_id: Optional[str] = None, line_items: Optional[List[Dict[str, Any]]] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Invoice]:
        if customer_id not in self._customers:
            return None
        inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        now = time.time()
        invoice = Invoice(id=inv_id, customer_id=customer_id, subscription_id=subscription_id, amount=amount, currency=currency, description=description, due_at=now + 30 * 86400, line_items=line_items or [], metadata=metadata or {})
        self._invoices[inv_id] = invoice
        return invoice

    def pay_invoice(self, invoice_id: str) -> Optional[Invoice]:
        invoice = self._invoices.get(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.PENDING:
            return None
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = time.time()
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)

    def list_invoices(self, customer_id: Optional[str] = None, status: Optional[InvoiceStatus] = None, limit: int = 100) -> List[Invoice]:
        invoices = list(self._invoices.values())
        if customer_id:
            invoices = [i for i in invoices if i.customer_id == customer_id]
        if status:
            invoices = [i for i in invoices if i.status == status]
        return invoices[-limit:]

    def get_usage(self, customer_id: str) -> Dict[str, Any]:
        customer = self._customers.get(customer_id)
        if not customer:
            return {"error": "Customer not found"}
        limits = PLAN_LIMITS.get(customer.plan, PLAN_LIMITS[BillingPlan.FREE])
        invoices = self.list_invoices(customer_id=customer_id, status=InvoiceStatus.PAID)
        total_paid = sum(inv.amount for inv in invoices)
        sub = None
        for s in self._subscriptions.values():
            if s.customer_id == customer_id and s.status == SubscriptionStatus.ACTIVE:
                sub = s
                break
        return {"customer_id": customer_id, "plan": customer.plan.value, "limits": limits, "total_paid": total_paid, "invoice_count": len(invoices), "active_subscription": sub.to_dict() if sub else None}

    def get_revenue_stats(self) -> Dict[str, Any]:
        invoices = list(self._invoices.values())
        paid = [i for i in invoices if i.status == InvoiceStatus.PAID]
        total_revenue = sum(i.amount for i in paid)
        pending = [i for i in invoices if i.status == InvoiceStatus.PENDING]
        pending_amount = sum(i.amount for i in pending)
        return {"total_revenue": total_revenue, "pending_amount": pending_amount, "total_invoices": len(invoices), "paid_invoices": len(paid), "total_customers": len(self._customers), "active_subscriptions": len([s for s in self._subscriptions.values() if s.status == SubscriptionStatus.ACTIVE])}

    def get_plan_info(self, plan: Optional[BillingPlan] = None) -> Dict[str, Any]:
        if plan:
            return {"plan": plan.value, "pricing": PLAN_PRICING[plan], "limits": PLAN_LIMITS[plan]}
        return {p.value: {"pricing": PLAN_PRICING[p], "limits": PLAN_LIMITS[p]} for p in BillingPlan}
