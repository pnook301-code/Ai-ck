"""License key system — generate, validate, expire, feature gating."""
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LicenseStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class LicenseTier(Enum):
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


TIER_FEATURES = {
    LicenseTier.TRIAL: ["basic_functions", "single_agent", "community_support"],
    LicenseTier.STARTER: ["basic_functions", "single_agent", "email_support", "5_tenants"],
    LicenseTier.PROFESSIONAL: ["all_functions", "multi_agent", "priority_support", "50_tenants", "audit_log"],
    LicenseTier.ENTERPRISE: ["all_functions", "multi_agent", "dedicated_support", "unlimited_tenants", "audit_log", "sso", "custom_branding"],
}


@dataclass
class License:
    id: str
    key: str
    tenant_id: str
    tier: LicenseTier
    status: LicenseStatus = LicenseStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    features: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_users: int = 5
    max_api_calls: int = 10000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "key": self.key, "tenant_id": self.tenant_id,
            "tier": self.tier.value, "status": self.status.value,
            "created_at": self.created_at, "expires_at": self.expires_at,
            "features": self.features, "metadata": self.metadata,
            "max_users": self.max_users, "max_api_calls": self.max_api_calls,
        }


def generate_license_key(tier: LicenseTier, tenant_id: str) -> str:
    raw = f"CK-{tier.value.upper()}-{tenant_id}-{uuid.uuid4().hex}"
    return f"CK{hashlib.sha256(raw.encode()).hexdigest()[:32].upper()}"


class LicenseManager:
    def __init__(self):
        self._licenses: Dict[str, License] = {}  # key → License
        self._by_tenant: Dict[str, List[str]] = {}  # tenant_id → [keys]

    def generate_license(self, tenant_id: str, tier: LicenseTier,
                         duration_days: Optional[int] = None,
                         max_users: Optional[int] = None,
                         max_api_calls: Optional[int] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> License:
        lid = f"lic_{uuid.uuid4().hex[:12]}"
        key = generate_license_key(tier, tenant_id)
        expires_at = time.time() + (duration_days * 86400) if duration_days else None

        tier_limits = {
            LicenseTier.TRIAL: (5, 1000),
            LicenseTier.STARTER: (20, 100000),
            LicenseTier.PROFESSIONAL: (100, 1000000),
            LicenseTier.ENTERPRISE: (999999, 999999),
        }
        default_users, default_calls = tier_limits.get(tier, (5, 10000))

        license_obj = License(
            id=lid, key=key, tenant_id=tenant_id, tier=tier,
            expires_at=expires_at,
            features=TIER_FEATURES.get(tier, []),
            metadata=metadata or {},
            max_users=max_users or default_users,
            max_api_calls=max_api_calls or default_calls,
        )
        self._licenses[key] = license_obj
        self._by_tenant.setdefault(tenant_id, []).append(key)
        return license_obj

    def validate_license(self, key: str) -> Dict[str, Any]:
        lic = self._licenses.get(key)
        if not lic:
            return {"valid": False, "reason": "License not found"}
        if lic.status == LicenseStatus.REVOKED:
            return {"valid": False, "reason": "License revoked"}
        if lic.status == LicenseStatus.SUSPENDED:
            return {"valid": False, "reason": "License suspended"}
        if lic.expires_at and time.time() > lic.expires_at:
            lic.status = LicenseStatus.EXPIRED
            return {"valid": False, "reason": "License expired"}
        return {"valid": True, "tier": lic.tier.value, "features": lic.features}

    def has_feature(self, key: str, feature: str) -> bool:
        result = self.validate_license(key)
        return result.get("valid", False) and feature in result.get("features", [])

    def revoke_license(self, key: str) -> bool:
        lic = self._licenses.get(key)
        if not lic:
            return False
        lic.status = LicenseStatus.REVOKED
        return True

    def suspend_license(self, key: str) -> bool:
        lic = self._licenses.get(key)
        if not lic:
            return False
        lic.status = LicenseStatus.SUSPENDED
        return True

    def get_license(self, key: str) -> Optional[License]:
        return self._licenses.get(key)

    def list_licenses(self, tenant_id: Optional[str] = None) -> List[License]:
        if tenant_id:
            keys = self._by_tenant.get(tenant_id, [])
            return [self._licenses[k] for k in keys if k in self._licenses]
        return list(self._licenses.values())

    def get_stats(self) -> Dict[str, Any]:
        licenses = list(self._licenses.values())
        active = [l for l in licenses if l.status == LicenseStatus.ACTIVE]
        return {
            "total": len(licenses),
            "active": len(active),
            "expired": len([l for l in licenses if l.status == LicenseStatus.EXPIRED]),
            "revoked": len([l for l in licenses if l.status == LicenseStatus.REVOKED]),
            "by_tier": {t.value: len([l for l in active if l.tier == t]) for t in LicenseTier},
        }
