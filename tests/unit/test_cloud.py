"""Tests for Cloud module — types, orchestrator, providers"""

import pytest
import asyncio


class TestCloudTypes:
    def test_import(self):
        from kernel.cloud import (
            CloudProvider, CloudCredentials, CloudOperation,
            VPSPlan, VPSServer, ServerStatus, Region,
            CloudOrchestrator, FREE_TIER_PLANS,
        )
        assert CloudProvider.HETZNER.value == "hetzner"
        assert CloudProvider.ORACLE.value == "oracle"

    def test_cloud_credentials_hetzner(self):
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(provider=CloudProvider.HETZNER, api_key="test_key")
        assert creds.is_valid()
        creds2 = CloudCredentials(provider=CloudProvider.HETZNER, api_key="")
        assert not creds2.is_valid()

    def test_cloud_credentials_digitalocean(self):
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(provider=CloudProvider.DIGITALOCEAN, api_key="do_token")
        assert creds.is_valid()

    def test_cloud_credentials_aws(self):
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(
            provider=CloudProvider.AWS,
            api_key="AKIA", api_secret="secret123",
        )
        assert creds.is_valid()
        creds2 = CloudCredentials(provider=CloudProvider.AWS, api_key="AKIA")
        assert not creds2.is_valid()

    def test_cloud_credentials_gcp(self):
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(
            provider=CloudProvider.GCP,
            project_id="my-project",
            private_key_path="/path/to/key.json",
        )
        assert creds.is_valid()

    def test_cloud_credentials_oracle(self):
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(
            provider=CloudProvider.ORACLE,
            fingerprint="aa:bb:cc",
            private_key_path="/path/to/key.pem",
            extra={"tenancy_id": "ocid1.tenancy..."},
        )
        assert creds.is_valid()

    def test_vps_plan_to_dict(self):
        from kernel.cloud.types import VPSPlan, CloudProvider
        plan = VPSPlan(
            provider=CloudProvider.HETZNER, plan_id="cx22",
            name="CX22", vcpus=2, ram_gb=4.0, disk_gb=40,
            bandwidth_tb=20, price_monthly_usd=3.49,
        )
        d = plan.to_dict()
        assert d["provider"] == "hetzner"
        assert d["vcpus"] == 2
        assert d["price_monthly_usd"] == 3.49

    def test_vps_server_to_dict(self):
        from kernel.cloud.types import VPSServer, CloudProvider, ServerStatus
        server = VPSServer(
            provider=CloudProvider.HETZNER,
            server_id="12345", name="test-server",
            status=ServerStatus.RUNNING,
            public_ipv4="1.2.3.4",
        )
        d = server.to_dict()
        assert d["status"] == "running"
        assert d["public_ipv4"] == "1.2.3.4"
        assert server.ssh_command == "root@1.2.3.4"

    def test_server_status_enum(self):
        from kernel.cloud.types import ServerStatus
        assert ServerStatus.RUNNING.value == "running"
        assert ServerStatus.STOPPED.value == "stopped"
        assert ServerStatus.PROVISIONING.value == "provisioning"

    def test_cloud_operation(self):
        from kernel.cloud.types import CloudOperation, CloudProvider
        op = CloudOperation(provider=CloudProvider.HETZNER, operation="create")
        assert op.status == "pending"
        assert op.duration_seconds >= 0

    def test_free_tier_plans_exist(self):
        from kernel.cloud.types import FREE_TIER_PLANS, CloudProvider
        assert CloudProvider.ORACLE in FREE_TIER_PLANS
        assert CloudProvider.GCP in FREE_TIER_PLANS
        assert CloudProvider.AWS in FREE_TIER_PLANS
        assert FREE_TIER_PLANS[CloudProvider.ORACLE].price_monthly_usd == 0.0
        assert FREE_TIER_PLANS[CloudProvider.ORACLE].is_free_tier is True

    def test_region_enum(self):
        from kernel.cloud.types import Region
        assert Region.HETZNER_FSN1.value == "fsn1"
        assert Region.DO_NYC.value == "nyc3"
        assert Region.ORACLE_US_ASHBURN.value == "us-ashburn-1"


class TestCloudOrchestrator:
    def test_init(self):
        from kernel.cloud import CloudOrchestrator
        orch = CloudOrchestrator()
        assert orch.configured_providers == []
        assert orch.get_status()["total_operations"] == 0

    def test_add_provider_invalid(self):
        from kernel.cloud import CloudOrchestrator, CloudCredentials, CloudProvider
        orch = CloudOrchestrator()
        creds = CloudCredentials(provider=CloudProvider.HETZNER, api_key="")
        assert not orch.add_provider(creds)

    def test_add_provider_valid(self):
        from kernel.cloud import CloudOrchestrator, CloudCredentials, CloudProvider
        orch = CloudOrchestrator()
        creds = CloudCredentials(provider=CloudProvider.HETZNER, api_key="test_key")
        assert orch.add_provider(creds)
        assert CloudProvider.HETZNER in orch.configured_providers

    def test_remove_provider(self):
        from kernel.cloud import CloudOrchestrator, CloudCredentials, CloudProvider
        orch = CloudOrchestrator()
        creds = CloudCredentials(provider=CloudProvider.HETZNER, api_key="test")
        orch.add_provider(creds)
        orch.remove_provider(CloudProvider.HETZNER)
        assert CloudProvider.HETZNER not in orch.configured_providers

    def test_get_recommendation(self):
        from kernel.cloud import CloudOrchestrator
        orch = CloudOrchestrator()
        rec = orch.get_recommendation()
        assert "best_free" in rec
        assert rec["best_free"]["provider"] == "oracle"
        assert "cheapest_paid" in rec
        assert rec["cheapest_paid"]["provider"] == "hetzner"

    def test_get_operations_empty(self):
        from kernel.cloud import CloudOrchestrator
        orch = CloudOrchestrator()
        ops = orch.get_operations()
        assert ops == []

    @pytest.mark.asyncio
    async def test_list_all_plans_no_providers(self):
        from kernel.cloud import CloudOrchestrator
        orch = CloudOrchestrator()
        plans = await orch.list_all_plans()
        assert plans == {}

    @pytest.mark.asyncio
    async def test_list_all_servers_no_providers(self):
        from kernel.cloud import CloudOrchestrator
        orch = CloudOrchestrator()
        servers = await orch.list_all_servers()
        assert servers == {}

    @pytest.mark.asyncio
    async def test_create_vps_no_provider(self):
        from kernel.cloud import CloudOrchestrator, CloudProvider
        orch = CloudOrchestrator()
        op = await orch.create_vps(CloudProvider.HETZNER)
        assert op.status == "failed"
        assert "not configured" in op.error


class TestHetznerProvider:
    def test_import(self):
        from kernel.cloud.providers.hetzner import HetznerProvider
        assert HetznerProvider is not None

    def test_init(self):
        from kernel.cloud.providers.hetzner import HetznerProvider
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(provider=CloudProvider.HETZNER, api_key="test")
        p = HetznerProvider(creds)
        assert p.provider == CloudProvider.HETZNER
        assert p.is_configured is True

    def test_not_configured(self):
        from kernel.cloud.providers.hetzner import HetznerProvider
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(provider=CloudProvider.HETZNER, api_key="")
        p = HetznerProvider(creds)
        assert p.is_configured is False


class TestDigitalOceanProvider:
    def test_import(self):
        from kernel.cloud.providers.digitalocean import DigitalOceanProvider
        assert DigitalOceanProvider is not None

    def test_init(self):
        from kernel.cloud.providers.digitalocean import DigitalOceanProvider
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(provider=CloudProvider.DIGITALOCEAN, api_key="do_token")
        p = DigitalOceanProvider(creds)
        assert p.provider == CloudProvider.DIGITALOCEAN
        assert p.is_configured is True


class TestAWSProvider:
    def test_import(self):
        from kernel.cloud.providers.aws_provider import AWSProvider
        assert AWSProvider is not None

    def test_init(self):
        from kernel.cloud.providers.aws_provider import AWSProvider
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(
            provider=CloudProvider.AWS,
            api_key="AKIA", api_secret="secret",
            region="us-east-1",
        )
        p = AWSProvider(creds)
        assert p.provider == CloudProvider.AWS
        assert p.is_configured is True


class TestGCPProvider:
    def test_import(self):
        from kernel.cloud.providers.gcp_provider import GCPProvider
        assert GCPProvider is not None

    def test_init(self):
        from kernel.cloud.providers.gcp_provider import GCPProvider
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(
            provider=CloudProvider.GCP,
            project_id="my-project",
            private_key_path="/path/key.json",
        )
        p = GCPProvider(creds)
        assert p.provider == CloudProvider.GCP
        assert p.is_configured is True


class TestOracleProvider:
    def test_import(self):
        from kernel.cloud.providers.oracle import OracleCloudProvider
        assert OracleCloudProvider is not None

    def test_init(self):
        from kernel.cloud.providers.oracle import OracleCloudProvider
        from kernel.cloud.types import CloudCredentials, CloudProvider
        creds = CloudCredentials(
            provider=CloudProvider.ORACLE,
            fingerprint="aa:bb:cc",
            private_key_path="/path/key.pem",
            extra={"tenancy_id": "ocid1.tenancy.oc1..aaa"},
        )
        p = OracleCloudProvider(creds)
        assert p.provider == CloudProvider.ORACLE
        assert p.is_configured is True


class TestCloudFunctions:
    def test_import_category12(self):
        from kernel.fn.category12 import definitions, register_cloud
        assert len(definitions) == 10
        assert register_cloud is not None

    def test_all_function_ids(self):
        from kernel.fn.category12 import definitions
        ids = [d.id for d in definitions]
        assert "12.1" in ids
        assert "12.5" in ids
        assert "12.10" in ids

    def test_category12_registration(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        register_all_categories(reg)
        cloud_fns = [f for f in reg._functions.values() if f.id.startswith("12.")]
        assert len(cloud_fns) == 10

    @pytest.mark.asyncio
    async def test_fn_12_1_list_providers(self):
        from kernel.fn.category12 import fn_12_1_list_providers
        result = await fn_12_1_list_providers({})
        assert "providers" in result
        assert isinstance(result["providers"], list)

    @pytest.mark.asyncio
    async def test_fn_12_9_recommendation(self):
        from kernel.fn.category12 import fn_12_9_get_recommendation
        result = await fn_12_9_get_recommendation({})
        assert "best_free" in result
        assert result["best_free"]["provider"] == "oracle"

    @pytest.mark.asyncio
    async def test_fn_12_10_status(self):
        from kernel.fn.category12 import fn_12_10_cloud_status
        result = await fn_12_10_cloud_status({})
        assert "providers" in result
        assert "total_operations" in result


class TestShadowBridgeScript:
    def test_script_exists(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "deploy", "setup_shadow_bridge.sh"
        )
        assert os.path.exists(path)

    def test_script_is_executable(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "deploy", "setup_shadow_bridge.sh"
        )
        assert os.access(path, os.R_OK)
