"""Cloud Orchestrator — multi-provider VPS management + one-click CK-NEXUS deploy"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .types import (
    CloudCredentials, CloudOperation, CloudProvider,
    VPSPlan, VPSServer, ServerStatus,
    FREE_TIER_PLANS, DEFAULT_SSH_KEY_NAME, DEFAULT_OS_IMAGE,
    INSTALL_SCRIPT_URL,
)
from .base import BaseCloudProvider

logger = logging.getLogger(__name__)


def _get_provider(credentials: CloudCredentials) -> BaseCloudProvider:
    """Factory: get the right provider class"""
    p = credentials.provider
    if p == CloudProvider.HETZNER:
        from .providers.hetzner import HetznerProvider
        return HetznerProvider(credentials)
    if p == CloudProvider.DIGITALOCEAN:
        from .providers.digitalocean import DigitalOceanProvider
        return DigitalOceanProvider(credentials)
    if p == CloudProvider.AWS:
        from .providers.aws_provider import AWSProvider
        return AWSProvider(credentials)
    if p == CloudProvider.GCP:
        from .providers.gcp_provider import GCPProvider
        return GCPProvider(credentials)
    if p == CloudProvider.ORACLE:
        from .providers.oracle import OracleCloudProvider
        return OracleCloudProvider(credentials)
    raise ValueError(f"Unknown provider: {p}")


class CloudOrchestrator:
    """Multi-cloud orchestrator — manages providers, creates VPS, deploys CK-NEXUS"""

    def __init__(self):
        self._providers: Dict[CloudProvider, BaseCloudProvider] = {}
        self._operations: List[CloudOperation] = []

    def add_provider(self, credentials: CloudCredentials) -> bool:
        """Register a cloud provider with credentials"""
        if not credentials.is_valid():
            logger.warning("Invalid credentials for %s", credentials.provider.value)
            return False
        provider = _get_provider(credentials)
        self._providers[credentials.provider] = provider
        logger.info("Registered provider: %s", credentials.provider.value)
        return True

    def remove_provider(self, provider: CloudProvider):
        self._providers.pop(provider, None)

    def get_provider(self, provider: CloudProvider) -> Optional[BaseCloudProvider]:
        return self._providers.get(provider)

    @property
    def configured_providers(self) -> List[CloudProvider]:
        return list(self._providers.keys())

    async def list_all_plans(self) -> Dict[str, List[Dict]]:
        """List plans from all configured providers"""
        result = {}
        for name, provider in self._providers.items():
            try:
                plans = await provider.list_plans()
                result[name.value] = [p.to_dict() for p in plans]
            except Exception as e:
                result[name.value] = [{"error": str(e)}]
        return result

    async def list_free_plans(self) -> List[Dict]:
        """Get free tier plans from all providers"""
        free = []
        for name, provider in self._providers.items():
            try:
                plans = await provider.get_free_plans()
                free.extend(p.to_dict() for p in plans)
            except Exception:
                pass
        return free

    async def list_all_servers(self) -> Dict[str, List[Dict]]:
        """List all servers from all providers"""
        result = {}
        for name, provider in self._providers.items():
            try:
                servers = await provider.list_servers()
                result[name.value] = [s.to_dict() for s in servers]
            except Exception as e:
                result[name.value] = [{"error": str(e)}]
        return result

    async def create_vps(
        self,
        provider: CloudProvider,
        name: str = "ck-nexus-aios",
        plan_id: str = "",
        region: str = "",
        image: str = "",
        ssh_public_key: str = "",
        user_data: str = "",
    ) -> CloudOperation:
        """Create a VPS on the specified provider"""
        prov = self._providers.get(provider)
        if not prov:
            op = CloudOperation(provider=provider, operation="create_vps")
            op.fail(f"Provider {provider.value} not configured")
            self._operations.append(op)
            return op

        op = CloudOperation(provider=provider, operation="create_vps")
        self._operations.append(op)
        op.logs.append(f"Creating VPS '{name}' on {provider.value}")

        try:
            # Use free tier plan if no plan specified
            if not plan_id and provider in FREE_TIER_PLANS:
                plan_id = FREE_TIER_PLANS[provider].plan_id
            if not image:
                image = DEFAULT_OS_IMAGE.get(provider, "ubuntu-22.04")
            if not region:
                region_map = {
                    CloudProvider.HETZNER: "fsn1",
                    CloudProvider.DIGITALOCEAN: "nyc3",
                    CloudProvider.AWS: "us-east-1",
                    CloudProvider.GCP: "us-central1-a",
                    CloudProvider.ORACLE: "us-ashburn-1",
                }
                region = region_map.get(provider, "")

            ssh_keys = [ssh_public_key] if ssh_public_key else []

            op.logs.append(f"Plan: {plan_id}, Region: {region}, Image: {image}")
            server = await prov.create_server(
                name=name, plan_id=plan_id, region=region,
                image=image, ssh_keys=ssh_keys, user_data=user_data,
            )
            op.complete(server)
            op.logs.append(f"Server created: {server.server_id} ({server.ip_address})")

        except Exception as e:
            op.fail(str(e))
            op.logs.append(f"Error: {e}")

        return op

    async def create_and_deploy(
        self,
        provider: CloudProvider,
        name: str = "ck-nexus-aios",
        plan_id: str = "",
        region: str = "",
        ssh_public_key: str = "",
        deploy_script: str = "",
    ) -> CloudOperation:
        """One-click: Create VPS + install CK-NEXUS automatically"""
        prov = self._providers.get(provider)
        if not prov:
            op = CloudOperation(provider=provider, operation="create_and_deploy")
            op.fail(f"Provider {provider.value} not configured")
            self._operations.append(op)
            return op

        op = CloudOperation(provider=provider, operation="create_and_deploy")
        self._operations.append(op)
        op.logs.append("=== One-Click Deploy: CK-NEXUS AIOS ===")

        try:
            # Step 1: Create VPS
            op.logs.append("[1/3] Creating VPS...")
            script = deploy_script or (
                f"#!/bin/bash\n"
                f"set -e\n"
                f"apt-get update && apt-get install -y curl git\n"
                f"curl -sSL {INSTALL_SCRIPT_URL} | bash\n"
            )

            create_op = await self.create_vps(
                provider=provider, name=name, plan_id=plan_id,
                region=region, ssh_public_key=ssh_public_key,
                user_data=script,
            )
            if create_op.status == "failed":
                op.fail(f"VPS creation failed: {create_op.error}")
                return op

            server = create_op.server
            op.logs.append(f"VPS ready: {server.ip_address}")

            # Step 2: Wait for server to be running
            op.logs.append("[2/3] Waiting for server to be ready...")
            try:
                await prov.wait_for_status(
                    server.server_id, ServerStatus.RUNNING, timeout=300,
                )
            except TimeoutError:
                op.logs.append("Warning: Timeout waiting for RUNNING, continuing...")

            # Step 3: Deploy via SSH (if SSH key available)
            op.logs.append("[3/3] Deploying CK-NEXUS...")
            if ssh_public_key and server.ip_address:
                deploy_result = await self._ssh_deploy(
                    server.ip_address, script,
                )
                op.logs.append(f"Deploy result: {deploy_result}")
            else:
                op.logs.append("SSH key not provided — user_data script will auto-install on boot")

            op.complete(server)
            op.logs.append(f"=== Deploy complete: http://{server.ip_address}:3000 ===")

        except Exception as e:
            op.fail(str(e))
            op.logs.append(f"Error: {e}")

        return op

    async def delete_vps(self, provider: CloudProvider, server_id: str) -> bool:
        """Delete a VPS"""
        prov = self._providers.get(provider)
        if not prov:
            return False
        return await prov.delete_server(server_id)

    async def get_server_status(
        self, provider: CloudProvider, server_id: str,
    ) -> Optional[VPSServer]:
        prov = self._providers.get(provider)
        if not prov:
            return None
        return await prov.get_server(server_id)

    async def _ssh_deploy(self, ip: str, script: str) -> str:
        """Deploy via SSH using paramiko"""
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username="root", timeout=30)
            stdin, stdout, stderr = client.exec_command(script, timeout=300)
            output = stdout.read().decode()
            errors = stderr.read().decode()
            client.close()
            return f"stdout: {output[-500:]}\nstderr: {errors[-500:]}"
        except ImportError:
            return "paramiko not installed — skipping SSH deploy"
        except Exception as e:
            return f"SSH deploy failed: {e}"

    def get_operation(self, op_id: str) -> Optional[CloudOperation]:
        for op in self._operations:
            if op.id == op_id:
                return op
        return None

    def get_operations(self, limit: int = 20) -> List[Dict]:
        return [{
            "id": op.id,
            "provider": op.provider.value,
            "operation": op.operation,
            "status": op.status,
            "error": op.error,
            "duration_s": op.duration_seconds,
            "logs": op.logs,
            "server": op.server.to_dict() if op.server else None,
        } for op in self._operations[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        return {
            "providers": [p.value for p in self._providers.keys()],
            "total_operations": len(self._operations),
            "successful": sum(1 for o in self._operations if o.status == "completed"),
            "failed": sum(1 for o in self._operations if o.status == "failed"),
        }

    def get_recommendation(self) -> Dict[str, Any]:
        """Recommend best provider based on needs"""
        return {
            "best_free": {
                "provider": "oracle",
                "plan": "VM.Standard.E2.1.Micro",
                "reason": "Free forever — no credit card trial, no time limit",
                "specs": "1 OCPU, 1 GB RAM, 50 GB storage, 10 TB transfer",
            },
            "cheapest_paid": {
                "provider": "hetzner",
                "plan": "cx22",
                "price": "$3.49/mo",
                "reason": "Best price/performance in EU",
                "specs": "2 vCPU, 4 GB RAM, 40 GB SSD, 20 TB transfer",
            },
            "best_trial": {
                "provider": "digitalocean",
                "plan": "$200 credit for 60 days",
                "reason": "Try any plan size during trial",
            },
            "best_for_production": {
                "provider": "aws",
                "plan": "t3.small",
                "reason": "Most mature ecosystem, 12-month free tier",
            },
        }
