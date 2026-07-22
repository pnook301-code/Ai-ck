"""Tests for Billing Module — Plans, Invoices, Subscriptions (15 tests)."""
import time
import pytest
from kernel.enterprise.billing import (
    BillingManager, BillingPlan, Customer, Subscription, Invoice,
    InvoiceStatus, SubscriptionStatus, PLAN_PRICING, PLAN_LIMITS,
)


class TestBillingTypes:
    def test_import(self):
        assert BillingManager is not None

    def test_plan_pricing(self):
        assert PLAN_PRICING[BillingPlan.FREE]["monthly"] == 0
        assert PLAN_PRICING[BillingPlan.STARTER]["monthly"] == 49
        assert PLAN_PRICING[BillingPlan.PROFESSIONAL]["monthly"] == 199

    def test_plan_limits(self):
        assert PLAN_LIMITS[BillingPlan.FREE]["max_users"] == 5
        assert PLAN_LIMITS[BillingPlan.ENTERPRISE]["max_users"] == -1

    def test_customer_to_dict(self):
        c = Customer(id="c1", tenant_id="t1", email="a@b.com", name="Test")
        d = c.to_dict()
        assert d["id"] == "c1"
        assert d["email"] == "a@b.com"

    def test_invoice_to_dict(self):
        inv = Invoice(id="i1", customer_id="c1", subscription_id=None, amount=4900, currency="USD")
        d = inv.to_dict()
        assert d["amount"] == 4900
        assert d["status"] == "pending"


class TestBillingManager:
    def test_create_customer(self):
        mgr = BillingManager()
        c = mgr.create_customer("t1", "a@b.com", "Test", BillingPlan.STARTER)
        assert c.plan == BillingPlan.STARTER

    def test_get_customer_by_tenant(self):
        mgr = BillingManager()
        mgr.create_customer("t1", "a@b.com", "Test")
        found = mgr.get_customer_by_tenant("t1")
        assert found is not None

    def test_create_subscription(self):
        mgr = BillingManager()
        c = mgr.create_customer("t1", "a@b.com", "Test")
        sub = mgr.create_subscription(c.id, BillingPlan.PROFESSIONAL)
        assert sub.plan == BillingPlan.PROFESSIONAL
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_cancel_subscription(self):
        mgr = BillingManager()
        c = mgr.create_customer("t1", "a@b.com", "Test")
        sub = mgr.create_subscription(c.id, BillingPlan.STARTER)
        cancelled = mgr.cancel_subscription(sub.id)
        assert cancelled.status == SubscriptionStatus.CANCELLED

    def test_create_and_pay_invoice(self):
        mgr = BillingManager()
        c = mgr.create_customer("t1", "a@b.com", "Test")
        inv = mgr.create_invoice(c.id, 4900, "USD", "Monthly")
        assert inv.status == InvoiceStatus.PENDING
        paid = mgr.pay_invoice(inv.id)
        assert paid.status == InvoiceStatus.PAID
        assert paid.paid_at is not None

    def test_usage(self):
        mgr = BillingManager()
        c = mgr.create_customer("t1", "a@b.com", "Test", BillingPlan.PROFESSIONAL)
        usage = mgr.get_usage(c.id)
        assert usage["plan"] == "professional"
        assert usage["limits"]["max_users"] == 100

    def test_revenue_stats(self):
        mgr = BillingManager()
        c = mgr.create_customer("t1", "a@b.com", "Test")
        mgr.create_invoice(c.id, 100, "USD")
        stats = mgr.get_revenue_stats()
        assert stats["total_invoices"] == 1

    def test_plan_info(self):
        mgr = BillingManager()
        info = mgr.get_plan_info()
        assert "free" in info
        assert "enterprise" in info
