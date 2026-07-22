"""Multi-tenant management — isolate data per tenant with RBAC."""
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TenantPlan(Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class Tenant:
    id: str
    name: str
    plan: TenantPlan = TenantPlan.FREE
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quotas: Dict[str, int] = field(default_factory=lambda: {
        "max_users": 5, "max_functions": 50, "max_storage_mb": 100,
        "max_api_calls": 10000, "max_agents": 2,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "plan": self.plan.value, "status": self.status.value,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "metadata": self.metadata, "quotas": self.quotas,
        }


PLAN_QUOTAS = {
    TenantPlan.FREE: {"max_users": 5, "max_functions": 50, "max_storage_mb": 100, "max_api_calls": 10000, "max_agents": 2},
    TenantPlan.STARTER: {"max_users": 20, "max_functions": 200, "max_storage_mb": 1000, "max_api_calls": 100000, "max_agents": 10},
    TenantPlan.PROFESSIONAL: {"max_users": 100, "max_functions": 500, "max_storage_mb": 10000, "max_api_calls": 1000000, "max_agents": 50},
    TenantPlan.ENTERPRISE: {"max_users": 999999, "max_functions": 999999, "max_storage_mb": 999999, "max_api_calls": 999999, "max_agents": 999999},
}


class TenantManager:
    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}

    def create_tenant(self, name: str, plan: TenantPlan = TenantPlan.FREE,
                      metadata: Optional[Dict[str, Any]] = None) -> Tenant:
        tid = f"tenant_{uuid.uuid4().hex[:12]}"
        tenant = Tenant(
            id=tid, name=name, plan=plan,
            quotas=PLAN_QUOTAS.get(plan, PLAN_QUOTAS[TenantPlan.FREE]),
            metadata=metadata or {},
        )
        self._tenants[tid] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def update_tenant(self, tenant_id: str, **kwargs) -> Optional[Tenant]:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        tenant.updated_at = time.time()
        return tenant

    def upgrade_plan(self, tenant_id: str, new_plan: TenantPlan) -> Optional[Tenant]:
        tenant = self._tenants.get(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return None
        tenant.plan = new_plan
        tenant.quotas = PLAN_QUOTAS[new_plan]
        tenant.updated_at = time.time()
        return tenant

    def suspend_tenant(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = time.time()
        return True

    def delete_tenant(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.DELETED
        tenant.updated_at = time.time()
        return True

    def get_stats(self) -> Dict[str, Any]:
        tenants = list(self._tenants.values())
        active = [t for t in tenants if t.status == TenantStatus.ACTIVE]
        return {
            "total": len(tenants),
            "active": len(active),
            "suspended": len([t for t in tenants if t.status == TenantStatus.SUSPENDED]),
            "by_plan": {plan.value: len([t for t in active if t.plan == plan]) for plan in TenantPlan},
        }
