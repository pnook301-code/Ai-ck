"""DigitalOcean Provider — simple cloud from $6/mo"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseCloudProvider
from ..types import (
    CloudCredentials, CloudProvider, VPSPlan, VPSServer, ServerStatus,
)

logger = logging.getLogger(__name__)

DO_API = "https://api.digitalocean.com/v2"


class DigitalOceanProvider(BaseCloudProvider):
    """DigitalOcean API integration"""

    def __init__(self, credentials: CloudCredentials):
        super().__init__(credentials)
        self._base_url = DO_API

    async def list_plans(self, region: str = "") -> List[VPSPlan]:
        data = await self._request("GET", "/sizes")
        plans = []
        for s in data.get("sizes", []):
            if not s.get("available"):
                continue
            plans.append(VPSPlan(
                provider=CloudProvider.DIGITALOCEAN,
                plan_id=s["slug"],
                name=f"DO {s['slug'].upper()}",
                vcpus=s["vcpus"],
                ram_gb=s["memory"] / 1024,
                disk_gb=s["disk"],
                bandwidth_tb=s.get("transfer", 1.0),
                price_monthly_usd=float(s["price_monthly"]),
                is_free_tier=False,
            ))
        return plans

    async def list_servers(self) -> List[VPSServer]:
        data = await self._request("GET", "/droplets")
        return [self._parse_server(d) for d in data.get("droplets", [])]

    async def create_server(
        self, name: str, plan_id: str, region: str = "nyc3",
        image: str = "ubuntu-22-04-x64", ssh_keys: List[str] = None,
        user_data: str = "",
    ) -> VPSServer:
        body = {
            "name": name,
            "region": region,
            "size": plan_id,
            "image": image,
            "ssh_keys": ssh_keys or [],
            "ipv6": True,
            "monitoring": True,
        }
        if user_data:
            body["user_data"] = user_data
        data = await self._request("POST", "/droplets", data=body)
        return self._parse_server(data["droplet"])

    async def delete_server(self, server_id: str) -> bool:
        await self._request("DELETE", f"/droplets/{server_id}")
        return True

    async def get_server(self, server_id: str) -> Optional[VPSServer]:
        try:
            data = await self._request("GET", f"/droplets/{server_id}")
            return self._parse_server(data["droplet"])
        except Exception:
            return None

    async def start_server(self, server_id: str) -> bool:
        await self._request("POST", f"/droplets/{server_id}/actions",
                          data={"type": "power_on"})
        return True

    async def stop_server(self, server_id: str) -> bool:
        await self._request("POST", f"/droplets/{server_id}/actions",
                          data={"type": "shutdown"})
        return True

    async def reboot_server(self, server_id: str) -> bool:
        await self._request("POST", f"/droplets/{server_id}/actions",
                          data={"type": "reboot"})
        return True

    async def list_ssh_keys(self) -> List[Dict]:
        data = await self._request("GET", "/account/keys")
        return data.get("ssh_keys", [])

    async def create_ssh_key(self, name: str, public_key: str) -> Dict:
        data = await self._request("POST", "/account/keys", data={
            "name": name, "public_key": public_key,
        })
        return data.get("ssh_key", {})

    def _parse_server(self, d: Dict) -> VPSServer:
        status_map = {
            "active": ServerStatus.RUNNING,
            "new": ServerStatus.PROVISIONING,
            "off": ServerStatus.STOPPED,
            "archive": ServerStatus.STOPPED,
        }
        networks = d.get("networks", {})
        v4 = networks.get("v4", [])
        public_ip = next((n["ip_address"] for n in v4 if n.get("type") == "public"), "")
        private_ip = next((n["ip_address"] for n in v4 if n.get("type") == "private"), "")
        v6 = networks.get("v6", [])
        ipv6 = next((n["ip_address"] for n in v6 if n.get("type") == "public"), "")

        return VPSServer(
            provider=CloudProvider.DIGITALOCEAN,
            server_id=str(d.get("id", "")),
            name=d.get("name", ""),
            status=status_map.get(d.get("status", ""), ServerStatus.UNKNOWN),
            ip_address=public_ip,
            public_ipv4=public_ip,
            private_ipv4=private_ip,
            ipv6=ipv6,
            region=d.get("region", {}).get("slug", ""),
            os_image=d.get("image", {}).get("slug", ""),
            created_at=d.get("created_at", ""),
        )
