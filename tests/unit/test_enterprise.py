"""Tests for Enterprise Module — Tenant, Audit, License (30 tests)."""
import time
import pytest
from kernel.enterprise.tenant import TenantManager, Tenant, TenantPlan, TenantStatus, PLAN_QUOTAS
from kernel.enterprise.audit import AuditLogger, AuditEvent, AuditAction, AuditSeverity
from kernel.enterprise.license import LicenseManager, License, LicenseTier, LicenseStatus, generate_license_key, TIER_FEATURES


class TestTenantTypes:
    def test_import(self):
        assert TenantManager is not None

    def test_create_tenant(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Acme Corp")
        assert t.name == "Acme Corp"
        assert t.plan == TenantPlan.FREE
        assert t.status == TenantStatus.ACTIVE
        assert t.id.startswith("tenant_")

    def test_create_tenant_enterprise(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Big Corp", TenantPlan.ENTERPRISE)
        assert t.plan == TenantPlan.ENTERPRISE
        assert t.quotas["max_users"] == 999999

    def test_tenant_to_dict(self):
        t = Tenant(id="t1", name="Test")
        d = t.to_dict()
        assert d["id"] == "t1"
        assert d["name"] == "Test"
        assert d["plan"] == "free"

    def test_plan_quotas_exist(self):
        for plan in TenantPlan:
            assert plan in PLAN_QUOTAS
            assert "max_users" in PLAN_QUOTAS[plan]

    def test_tenant_status_enum(self):
        assert TenantStatus.ACTIVE.value == "active"
        assert TenantStatus.SUSPENDED.value == "suspended"


class TestTenantManager:
    def test_get_tenant(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Test")
        assert mgr.get_tenant(t.id) is not None

    def test_get_tenant_not_found(self):
        mgr = TenantManager()
        assert mgr.get_tenant("nonexistent") is None

    def test_list_tenants(self):
        mgr = TenantManager()
        mgr.create_tenant("A")
        mgr.create_tenant("B")
        assert len(mgr.list_tenants()) == 2

    def test_list_tenants_by_status(self):
        mgr = TenantManager()
        t1 = mgr.create_tenant("A")
        mgr.create_tenant("B")
        mgr.suspend_tenant(t1.id)
        active = mgr.list_tenants(TenantStatus.ACTIVE)
        suspended = mgr.list_tenants(TenantStatus.SUSPENDED)
        assert len(active) == 1
        assert len(suspended) == 1

    def test_update_tenant(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Old Name")
        updated = mgr.update_tenant(t.id, name="New Name")
        assert updated.name == "New Name"

    def test_upgrade_plan(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Test")
        upgraded = mgr.upgrade_plan(t.id, TenantPlan.PROFESSIONAL)
        assert upgraded.plan == TenantPlan.PROFESSIONAL
        assert upgraded.quotas["max_users"] == 100

    def test_suspend_tenant(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Test")
        assert mgr.suspend_tenant(t.id) is True
        assert t.status == TenantStatus.SUSPENDED

    def test_delete_tenant(self):
        mgr = TenantManager()
        t = mgr.create_tenant("Test")
        assert mgr.delete_tenant(t.id) is True
        assert t.status == TenantStatus.DELETED

    def test_stats(self):
        mgr = TenantManager()
        mgr.create_tenant("A")
        mgr.create_tenant("B", TenantPlan.ENTERPRISE)
        stats = mgr.get_stats()
        assert stats["total"] == 2
        assert stats["active"] == 2
        assert stats["by_plan"]["free"] == 1
        assert stats["by_plan"]["enterprise"] == 1


class TestAuditTypes:
    def test_import(self):
        assert AuditLogger is not None

    def test_audit_action_enum(self):
        assert AuditAction.USER_LOGIN.value == "user.login"
        assert AuditAction.FUNCTION_EXECUTE.value == "function.execute"

    def test_audit_severity_enum(self):
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.CRITICAL.value == "critical"

    def test_audit_event_to_dict(self):
        event = AuditEvent(
            id="e1", timestamp=time.time(),
            action=AuditAction.USER_LOGIN, severity=AuditSeverity.INFO,
            tenant_id="t1", user_id="u1",
            resource_type="user", resource_id="u1",
        )
        d = event.to_dict()
        assert d["id"] == "e1"
        assert d["action"] == "user.login"


class TestAuditLogger:
    def test_log_event(self):
        log = AuditLogger()
        event = log.log(AuditAction.USER_LOGIN, tenant_id="t1", user_id="u1")
        assert event.id.startswith("audit_")
        assert event.action == AuditAction.USER_LOGIN

    def test_query_by_tenant(self):
        log = AuditLogger()
        log.log(AuditAction.USER_LOGIN, tenant_id="t1")
        log.log(AuditAction.USER_LOGIN, tenant_id="t2")
        results = log.query(tenant_id="t1")
        assert len(results) == 1

    def test_query_by_action(self):
        log = AuditLogger()
        log.log(AuditAction.USER_LOGIN)
        log.log(AuditAction.USER_LOGOUT)
        results = log.query(action=AuditAction.USER_LOGIN)
        assert len(results) == 1

    def test_query_by_severity(self):
        log = AuditLogger()
        log.log(AuditAction.ERROR, severity=AuditSeverity.ERROR)
        log.log(AuditAction.USER_LOGIN, severity=AuditSeverity.INFO)
        results = log.query(severity=AuditSeverity.ERROR)
        assert len(results) == 1

    def test_max_events_fifo(self):
        log = AuditLogger(max_events=5)
        for i in range(10):
            log.log(AuditAction.API_CALL)
        assert len(log._events) == 5

    def test_stats(self):
        log = AuditLogger()
        log.log(AuditAction.USER_LOGIN)
        log.log(AuditAction.ERROR, severity=AuditSeverity.ERROR, success=False)
        stats = log.get_stats()
        assert stats["total_events"] == 2
        assert stats["error_count"] == 1


class TestLicenseTypes:
    def test_import(self):
        assert LicenseManager is not None

    def test_generate_key(self):
        key = generate_license_key(LicenseTier.PROFESSIONAL, "tenant_123")
        assert key.startswith("CK")
        assert len(key) == 34  # CK + 32 hex

    def test_tier_features(self):
        assert "sso" in TIER_FEATURES[LicenseTier.ENTERPRISE]
        assert "sso" not in TIER_FEATURES[LicenseTier.STARTER]

    def test_license_to_dict(self):
        lic = License(id="l1", key="CK_TEST", tenant_id="t1", tier=LicenseTier.STARTER)
        d = lic.to_dict()
        assert d["tier"] == "starter"
        assert d["status"] == "active"


class TestLicenseManager:
    def test_generate_license(self):
        mgr = LicenseManager()
        lic = mgr.generate_license("tenant_1", LicenseTier.PROFESSIONAL, duration_days=30)
        assert lic.tier == LicenseTier.PROFESSIONAL
        assert lic.expires_at is not None
        assert "all_functions" in lic.features

    def test_validate_active(self):
        mgr = LicenseManager()
        lic = mgr.generate_license("tenant_1", LicenseTier.ENTERPRISE)
        result = mgr.validate_license(lic.key)
        assert result["valid"] is True
        assert result["tier"] == "enterprise"

    def test_validate_expired(self):
        mgr = LicenseManager()
        lic = mgr.generate_license("tenant_1", LicenseTier.TRIAL, duration_days=-1)
        result = mgr.validate_license(lic.key)
        assert result["valid"] is False
        assert "expired" in result["reason"]

    def test_validate_revoked(self):
        mgr = LicenseManager()
        lic = mgr.generate_license("tenant_1", LicenseTier.STARTER)
        mgr.revoke_license(lic.key)
        result = mgr.validate_license(lic.key)
        assert result["valid"] is False
        assert "revoked" in result["reason"]

    def test_validate_not_found(self):
        mgr = LicenseManager()
        result = mgr.validate_license("CK_NONEXISTENT")
        assert result["valid"] is False

    def test_has_feature(self):
        mgr = LicenseManager()
        lic = mgr.generate_license("t1", LicenseTier.ENTERPRISE)
        assert mgr.has_feature(lic.key, "sso") is True
        assert mgr.has_feature(lic.key, "nonexistent") is False

    def test_suspend_license(self):
        mgr = LicenseManager()
        lic = mgr.generate_license("t1", LicenseTier.STARTER)
        assert mgr.suspend_license(lic.key) is True
        result = mgr.validate_license(lic.key)
        assert result["valid"] is False

    def test_list_by_tenant(self):
        mgr = LicenseManager()
        mgr.generate_license("t1", LicenseTier.STARTER)
        mgr.generate_license("t1", LicenseTier.PROFESSIONAL)
        mgr.generate_license("t2", LicenseTier.TRIAL)
        t1_lics = mgr.list_licenses("t1")
        assert len(t1_lics) == 2

    def test_stats(self):
        mgr = LicenseManager()
        mgr.generate_license("t1", LicenseTier.STARTER)
        mgr.generate_license("t2", LicenseTier.ENTERPRISE)
        stats = mgr.get_stats()
        assert stats["total"] == 2
        assert stats["active"] == 2
