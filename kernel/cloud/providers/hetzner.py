"""Hetzner Cloud Provider — cheapest EU VPS from €3.49/mo"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseCloudProvider
from ..types import (
    CloudCredentials, CloudProvider, VPSPlan, VPSServer, ServerStatus,
)

logger = logging.getLogger(__name__)

HETZNER_API = "https://api.hetzner.cloud/v1"


class HetznerProvider(BaseCloudProvider):
    """Hetzner Cloud API integration"""

    def __init__(self, credentials: CloudCredentials):
        super().__init__(credentials)
        self._base_url = HETZNER_API

    async def list_plans(self, region: str = "") -> List[VPSPlan]:
        data = await self._request("GET", "/server_types")
        plans = []
        for st in data.get("server_types", []):
            plans.append(VPSPlan(
                provider=CloudProvider.HETZNER,
                plan_id=st["name"],
                name=f"Hetzner {st['name'].upper()}",
                vcpus=st["cores"],
                ram_gb=st["memory"] / 1024,
                disk_gb=st["disk"],
                bandwidth_tb=20.0,
                price_monthly_usd=st["prices"][0]["price"]["gross_monthly"]
                    if st.get("prices") else 0.0,
                is_free_tier=False,
            ))
        return plans

    async def list_servers(self) -> List[VPSServer]:
        data = await self._request("GET", "/servers")
        servers = []
        for s in data.get("servers", []):
            servers.append(self._parse_server(s))
        return servers

    async def create_server(
        self, name: str, plan_id: str, region: str = "fsn1",
        image: str = "ubuntu-22.04", ssh_keys: List[str] = None,
        user_data: str = "",
    ) -> VPSServer:
        body = {
            "name": name,
            "server_type": plan_id,
            "image": image,
            "location": region,
            "ssh_keys": ssh_keys or [],
            "start_after_create": True,
        }
        if user_data:
            body["user_data"] = user_data
        data = await self._request("POST", "/servers", data=body)
        return self._parse_server(data["server"])

    async def delete_server(self, server_id: str) -> bool:
        await self._request("DELETE", f"/servers/{server_id}")
        return True

    async def get_server(self, server_id: str) -> Optional[VPSServer]:
        try:
            data = await self._request("GET", f"/servers/{server_id}")
            return self._parse_server(data["server"])
        except Exception:
            return None

    async def start_server(self, server_id: str) -> bool:
        await self._request("POST", f"/servers/{server_id}/actions/poweron")
        return True

    async def stop_server(self, server_id: str) -> bool:
        await self._request("POST", f"/servers/{server_id}/actions/shutdown")
        return True

    async def reboot_server(self, server_id: str) -> bool:
        await self._request("POST", f"/servers/{server_id}/actions/reboot")
        return True

    async def list_ssh_keys(self) -> List[Dict]:
        data = await self._request("GET", "/ssh_keys")
        return data.get("ssh_keys", [])

    async def create_ssh_key(self, name: str, public_key: str) -> Dict:
        data = await self._request("POST", "/ssh_keys", data={
            "name": name, "public_key": public_key,
        })
        return data.get("ssh_key", {})

    def _parse_server(self, s: Dict) -> VPSServer:
        status_map = {
            "running": ServerStatus.RUNNING,
            "off": ServerStatus.STOPPED,
            "starting": ServerStatus.PROVISIONING,
            "stopping": ServerStatus.PROVISIONING,
            "rebuilding": ServerStatus.REBOOTING,
            "deleting": ServerStatus.DELETING,
            "error": ServerStatus.ERROR,
        }
        net = s.get("public_net", {})
        ipv4 = net.get("ipv4", {})
        ipv6 = net.get("ipv6", {})
        return VPSServer(
            provider=CloudProvider.HETZNER,
            server_id=str(s.get("id", "")),
            name=s.get("name", ""),
            status=status_map.get(s.get("status", ""), ServerStatus.UNKNOWN),
            ip_address=ipv4.get("ip", ""),
            public_ipv4=ipv4.get("ip", ""),
            ipv6=ipv6.get("ip", ""),
            region=s.get("datacenter", {}).get("location", {}).get("name", ""),
            os_image=s.get("image", {}).get("name", ""),
            created_at=s.get("created", ""),
            extra={"datacenter": s.get("datacenter", {}).get("name", "")},
        )
