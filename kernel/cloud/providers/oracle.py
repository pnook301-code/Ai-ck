"""Oracle Cloud Provider — Always Free Tier (AMD 1CPU/1GB forever)"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseCloudProvider
from ..types import (
    CloudCredentials, CloudProvider, VPSPlan, VPSServer, ServerStatus,
    FREE_TIER_PLANS,
)

logger = logging.getLogger(__name__)

OCI_API = "https://iaas.us-ashburn-1.oraclecloud.com"


class OracleCloudProvider(BaseCloudProvider):
    """Oracle Cloud Infrastructure — Always Free Tier

    Free forever:
    - VM.Standard.E2.1.Micro (1 OCPU, 1 GB RAM)
    - Up to 4 instances
    - 200 GB block storage
    - 10 GB object storage
    - 10 TB/month outbound data transfer

    Note: OCI API requires signing (RSA-SHA256). This provider
    supports key-based auth via fingerprint + private key PEM.
    """

    def __init__(self, credentials: CloudCredentials):
        super().__init__(credentials)
        self._base_url = OCI_API
        self._tenancy_id = credentials.extra.get("tenancy_id", "")
        self._user_id = credentials.extra.get("user_id", "")
        self._compartment_id = credentials.extra.get("compartment_id", self._tenancy_id)

    async def list_plans(self, region: str = "") -> List[VPSPlan]:
        free = FREE_TIER_PLANS[CloudProvider.ORACLE]
        return [
            free,
            VPSPlan(
                provider=CloudProvider.ORACLE,
                plan_id="VM.Standard.E2.1",
                name="E2.1 (1 OCPU / 8GB)",
                vcpus=1, ram_gb=8.0, disk_gb=200, bandwidth_tb=10,
                price_monthly_usd=8.0, is_free_tier=False,
            ),
            VPSPlan(
                provider=CloudProvider.ORACLE,
                plan_id="VM.Standard.E2.2",
                name="E2.2 (2 OCPU / 16GB)",
                vcpus=2, ram_gb=16.0, disk_gb=200, bandwidth_tb=10,
                price_monthly_usd=16.0, is_free_tier=False,
            ),
        ]

    async def list_servers(self) -> List[VPSServer]:
        """List instances — requires OCI API signing"""
        try:
            headers = self._sign_request("GET", "/instances")
            data = await self._request(
                "GET",
                f"/instances?compartmentId={self._compartment_id}",
                headers=headers,
            )
            return [self._parse_server(i) for i in data.get("items", [])]
        except Exception as e:
            logger.warning("Oracle list_servers failed: %s", e)
            return []

    async def create_server(
        self, name: str, plan_id: str, region: str = "us-ashburn-1",
        image: str = "Oracle-Linux-8.5-Gen2-Micro", ssh_keys: List[str] = None,
        user_data: str = "",
    ) -> VPSServer:
        """Create instance — OCI API with signing"""
        body = {
            "compartmentId": self._compartment_id,
            "displayName": name,
            "shape": plan_id,
            "sourceDetails": {
                "sourceType": "image",
                "imageId": self._get_image_id(image),
            },
            "createVnicDetails": {
                "subnetId": self._get_subnet_id(),
                "assignPublicIp": True,
            },
            "metadata": {},
        }
        if user_data:
            body["metadata"]["user_data"] = user_data
        if ssh_keys:
            body["metadata"]["ssh_authorized_keys"] = " ".join(ssh_keys)

        headers = self._sign_request("POST", "/instances")
        data = await self._request("POST", "/instances", data=body, headers=headers)
        return self._parse_server(data)

    async def delete_server(self, server_id: str) -> bool:
        headers = self._sign_request("DELETE", f"/instances/{server_id}")
        await self._request("DELETE", f"/instances/{server_id}", headers=headers)
        return True

    async def get_server(self, server_id: str) -> Optional[VPSServer]:
        try:
            headers = self._sign_request("GET", f"/instances/{server_id}")
            data = await self._request("GET", f"/instances/{server_id}", headers=headers)
            return self._parse_server(data)
        except Exception:
            return None

    async def start_server(self, server_id: str) -> bool:
        headers = self._sign_request("POST", f"/instances/{server_id}/actions")
        await self._request("POST", f"/instances/{server_id}/actions",
                          data={"action": "start"}, headers=headers)
        return True

    async def stop_server(self, server_id: str) -> bool:
        headers = self._sign_request("POST", f"/instances/{server_id}/actions")
        await self._request("POST", f"/instances/{server_id}/actions",
                          data={"action": "stop"}, headers=headers)
        return True

    async def reboot_server(self, server_id: str) -> bool:
        headers = self._sign_request("POST", f"/instances/{server_id}/actions")
        await self._request("POST", f"/instances/{server_id}/actions",
                          data={"action": "softreset"}, headers=headers)
        return True

    def _sign_request(self, method: str, path: str) -> Dict[str, str]:
        """Sign OCI request with RSA-SHA256 (placeholder — requires cryptography lib)"""
        return {
            "Authorization": f'Signature version="1",keyId="{self._creds.fingerprint}"',
            "Date": "",
            "Host": OCI_API.replace("https://", ""),
        }

    def _get_image_id(self, image: str) -> str:
        return self._creds.extra.get("image_id", "ocid1.image.oc1..placeholder")

    def _get_subnet_id(self) -> str:
        return self._creds.extra.get("subnet_id", "ocid1.subnet.oc1..placeholder")

    def _parse_server(self, s: Dict) -> VPSServer:
        life = s.get("lifecycleState", "")
        status_map = {
            "RUNNING": ServerStatus.RUNNING,
            "STOPPED": ServerStatus.STOPPED,
            "PROVISIONING": ServerStatus.PROVISIONING,
            "STARTING": ServerStatus.PROVISIONING,
            "STOPPING": ServerStatus.PROVISIONING,
            "TERMINATING": ServerStatus.DELETING,
            "TERMINATED": ServerStatus.DELETING,
        }
        vnic = s.get("vnicAttachments", [{}])
        ip = vnic[0].get("publicIp", "") if vnic else ""

        return VPSServer(
            provider=CloudProvider.ORACLE,
            server_id=s.get("id", ""),
            name=s.get("displayName", ""),
            status=status_map.get(life, ServerStatus.UNKNOWN),
            ip_address=ip,
            public_ipv4=ip,
            region=s.get("compartmentId", ""),
            os_image=s.get("sourceDetails", {}).get("imageId", ""),
            created_at=s.get("timeCreated", ""),
        )
