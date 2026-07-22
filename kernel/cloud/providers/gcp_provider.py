"""GCP Compute Engine Provider — Always Free e2-micro"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseCloudProvider
from ..types import (
    CloudCredentials, CloudProvider, VPSPlan, VPSServer, ServerStatus,
    FREE_TIER_PLANS,
)

logger = logging.getLogger(__name__)

GCP_COMPUTE_API = "https://compute.googleapis.com/compute/v1"


class GCPProvider(BaseCloudProvider):
    """Google Cloud Compute Engine — Always Free Tier

    Free forever (us-central1, us-east1, us-west1):
    - e2-micro (2 vCPU shared, 1 GB RAM)
    - 30 GB standard persistent disk
    - 1 GB outbound data transfer/month (US regions)
    """

    def __init__(self, credentials: CloudCredentials):
        super().__init__(credentials)
        self._project_id = credentials.project_id
        self._base_url = GCP_COMPUTE_API
        self._zone = credentials.extra.get("zone", "us-central1-a")

    @property
    def _auth_header(self) -> str:
        return f"Bearer {self._creds.api_key}"

    async def list_plans(self, region: str = "") -> List[VPSPlan]:
        free = FREE_TIER_PLANS[CloudProvider.GCP]
        return [
            free,
            VPSPlan(
                provider=CloudProvider.GCP, plan_id="e2-small",
                name="e2-small", vcpus=2, ram_gb=2.0, disk_gb=30,
                bandwidth_tb=1, price_monthly_usd=16.91, is_free_tier=False,
            ),
            VPSPlan(
                provider=CloudProvider.GCP, plan_id="e2-medium",
                name="e2-medium", vcpus=2, ram_gb=4.0, disk_gb=30,
                bandwidth_tb=1, price_monthly_usd=33.82, is_free_tier=False,
            ),
        ]

    async def list_servers(self) -> List[VPSServer]:
        path = f"/projects/{self._project_id}/aggregated/instances"
        try:
            data = await self._request("GET", path,
                                     headers={"Authorization": self._auth_header})
            servers = []
            for zone, items in data.get("items", {}).items():
                for inst in items.get("instances", []):
                    servers.append(self._parse_server(inst))
            return servers
        except Exception as e:
            logger.warning("GCP list_servers failed: %s", e)
            return []

    async def create_server(
        self, name: str, plan_id: str, region: str = "us-central1-a",
        image: str = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts",
        ssh_keys: List[str] = None,
        user_data: str = "",
    ) -> VPSServer:
        body = {
            "name": name,
            "machineType": f"zones/{self._zone}/machineTypes/{plan_id}",
            "disks": [{
                "boot": True,
                "autoDelete": True,
                "initializeParams": {
                    "sourceImage": image,
                    "diskSizeGb": "30",
                    "diskType": f"zones/{self._zone}/diskTypes/pd-standard",
                },
            }],
            "networkInterfaces": [{
                "network": "global/networks/default",
                "accessConfigs": [{"name": "External NAT", "type": "ONE_TO_ONE_NAT"}],
            }],
            "metadata": {},
        }
        if ssh_keys:
            body["metadata"]["items"] = [
                {"key": "ssh-keys", "value": "\n".join(
                    f"ubuntu:{k}" for k in ssh_keys
                )}
            ]
        if user_data:
            body["metadata"]["items"] = body["metadata"].get("items", []) + [
                {"key": "startup-script", "value": user_data}
            ]

        path = f"/projects/{self._project_id}/zones/{self._zone}/instances"
        data = await self._request("POST", path, data=body,
                                 headers={"Authorization": self._auth_header})
        return self._parse_server(data)

    async def delete_server(self, server_id: str) -> bool:
        path = f"/projects/{self._project_id}/zones/{self._zone}/instances/{server_id}"
        await self._request("DELETE", path, headers={"Authorization": self._auth_header})
        return True

    async def get_server(self, server_id: str) -> Optional[VPSServer]:
        try:
            path = f"/projects/{self._project_id}/zones/{self._zone}/instances/{server_id}"
            data = await self._request("GET", path,
                                     headers={"Authorization": self._auth_header})
            return self._parse_server(data)
        except Exception:
            return None

    async def start_server(self, server_id: str) -> bool:
        path = f"/projects/{self._project_id}/zones/{self._zone}/instances/{server_id}/start"
        await self._request("POST", path, headers={"Authorization": self._auth_header})
        return True

    async def stop_server(self, server_id: str) -> bool:
        path = f"/projects/{self._project_id}/zones/{self._zone}/instances/{server_id}/stop"
        await self._request("POST", path, headers={"Authorization": self._auth_header})
        return True

    async def reboot_server(self, server_id: str) -> bool:
        path = f"/projects/{self._project_id}/zones/{self._zone}/instances/{server_id}/reset"
        await self._request("POST", path, headers={"Authorization": self._auth_header})
        return True

    def _parse_server(self, inst: Dict) -> VPSServer:
        status = inst.get("status", "")
        status_map = {
            "RUNNING": ServerStatus.RUNNING,
            "TERMINATED": ServerStatus.STOPPED,
            "PROVISIONING": ServerStatus.PROVISIONING,
            "STAGING": ServerStatus.PROVISIONING,
            "STOPPING": ServerStatus.PROVISIONING,
            "REPAIRING": ServerStatus.REBOOTING,
        }
        nics = inst.get("networkInterfaces", [])
        external_ip = ""
        if nics and nics[0].get("accessConfigs"):
            external_ip = nics[0]["accessConfigs"][0].get("natIP", "")
        internal_ip = nics[0].get("networkIP", "") if nics else ""

        return VPSServer(
            provider=CloudProvider.GCP,
            server_id=str(inst.get("id", "")),
            name=inst.get("name", ""),
            status=status_map.get(status, ServerStatus.UNKNOWN),
            ip_address=external_ip,
            public_ipv4=external_ip,
            private_ipv4=internal_ip,
            zone=inst.get("zone", "").split("/")[-1],
            os_image=inst.get("disks", [{}])[0].get("sourceImage", "").split("/")[-1],
            created_at=inst.get("creationTimestamp", ""),
        )
