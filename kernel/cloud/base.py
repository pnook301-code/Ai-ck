"""Base Cloud Provider — abstract interface for all providers"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .types import (
    CloudCredentials, CloudOperation, CloudProvider,
    VPSPlan, VPSServer, ServerStatus,
)

logger = logging.getLogger(__name__)


class BaseCloudProvider(ABC):
    """Abstract base for cloud provider implementations"""

    def __init__(self, credentials: CloudCredentials):
        self._creds = credentials
        self._provider = credentials.provider
        self._base_url = ""
        self._timeout = 30

    @property
    def provider(self) -> CloudProvider:
        return self._provider

    @property
    def is_configured(self) -> bool:
        return self._creds.is_valid()

    @abstractmethod
    async def list_plans(self, region: str = "") -> List[VPSPlan]:
        """List available VPS plans"""
        ...

    @abstractmethod
    async def list_servers(self) -> List[VPSServer]:
        """List all existing servers"""
        ...

    @abstractmethod
    async def create_server(
        self, name: str, plan_id: str, region: str = "",
        image: str = "", ssh_keys: List[str] = None,
        user_data: str = "",
    ) -> VPSServer:
        """Create a new VPS server"""
        ...

    @abstractmethod
    async def delete_server(self, server_id: str) -> bool:
        """Delete a VPS server"""
        ...

    @abstractmethod
    async def get_server(self, server_id: str) -> Optional[VPSServer]:
        """Get server details by ID"""
        ...

    @abstractmethod
    async def start_server(self, server_id: str) -> bool:
        """Start a stopped server"""
        ...

    @abstractmethod
    async def stop_server(self, server_id: str) -> bool:
        """Stop a running server"""
        ...

    @abstractmethod
    async def reboot_server(self, server_id: str) -> bool:
        """Reboot a server"""
        ...

    async def wait_for_status(
        self, server_id: str, target_status: ServerStatus,
        timeout: int = 300, poll_interval: int = 5,
    ) -> VPSServer:
        """Poll until server reaches target status"""
        elapsed = 0
        while elapsed < timeout:
            server = await self.get_server(server_id)
            if server and server.status == target_status:
                return server
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(
            f"Server {server_id} did not reach {target_status.value} "
            f"within {timeout}s"
        )

    async def get_free_plans(self) -> List[VPSPlan]:
        """Get only free tier plans"""
        all_plans = await self.list_plans()
        return [p for p in all_plans if p.is_free_tier]

    async def _request(
        self, method: str, path: str,
        data: Dict = None, headers: Dict = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to provider API"""
        import aiohttp
        url = f"{self._base_url}{path}"
        hdrs = headers or {}
        if self._creds.api_key and "Authorization" not in hdrs:
            if self._provider == CloudProvider.HETZNER:
                hdrs["Authorization"] = f"Bearer {self._creds.api_key}"
            elif self._provider == CloudProvider.DIGITALOCEAN:
                hdrs["Authorization"] = f"Bearer {self._creds.api_key}"
            elif self._provider == CloudProvider.AWS:
                pass  # AWS uses sigv4, handled in aws_provider
        hdrs.setdefault("Content-Type", "application/json")

        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method, url, json=data, headers=hdrs,
            ) as resp:
                body = await resp.json()
                if resp.status >= 400:
                    raise Exception(
                        f"API error {resp.status}: {body}"
                    )
                return body
