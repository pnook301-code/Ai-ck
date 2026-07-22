"""AWS EC2 Provider — Free Tier t2.micro for 12 months"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseCloudProvider
from ..types import (
    CloudCredentials, CloudProvider, VPSPlan, VPSServer, ServerStatus,
    FREE_TIER_PLANS,
)

logger = logging.getLogger(__name__)


class AWSProvider(BaseCloudProvider):
    """AWS EC2 — Free Tier (t2.micro 12 months)

    Free Tier includes:
    - 750 hours/month t2.micro (Linux)
    - 30 GB EBS storage
    - 100 GB outbound data transfer
    """

    def __init__(self, credentials: CloudCredentials):
        super().__init__(credentials)
        self._region = credentials.region or "us-east-1"
        self._base_url = f"https://ec2.{self._region}.amazonaws.com"

    async def list_plans(self, region: str = "") -> List[VPSPlan]:
        free = FREE_TIER_PLANS[CloudProvider.AWS]
        return [
            free,
            VPSPlan(
                provider=CloudProvider.AWS, plan_id="t3.micro",
                name="t3.micro", vcpus=2, ram_gb=1.0, disk_gb=30,
                bandwidth_tb=1, price_monthly_usd=7.59, is_free_tier=False,
            ),
            VPSPlan(
                provider=CloudProvider.AWS, plan_id="t3.small",
                name="t3.small", vcpus=2, ram_gb=2.0, disk_gb=30,
                bandwidth_tb=1, price_monthly_usd=15.18, is_free_tier=False,
            ),
        ]

    async def list_servers(self) -> List[VPSServer]:
        """List EC2 instances via describe-instances"""
        try:
            data = await self._ec2_request("DescribeInstances")
            servers = []
            for reservation in data.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    servers.append(self._parse_server(inst))
            return servers
        except Exception as e:
            logger.warning("AWS list_servers failed: %s", e)
            return []

    async def create_server(
        self, name: str, plan_id: str, region: str = "us-east-1",
        image: str = "ami-0c02fb55956c7d316", ssh_keys: List[str] = None,
        user_data: str = "",
    ) -> VPSServer:
        params = {
            "Action": "RunInstances",
            "ImageId": image,
            "InstanceType": plan_id,
            "MinCount": "1",
            "MaxCount": "1",
            "KeyName": (ssh_keys or ["ck-nexus"])[0],
            "TagSpecification.1.ResourceType": "instance",
            "TagSpecification.1.Tag.1.Key": "Name",
            "TagSpecification.1.Tag.1.Value": name,
        }
        if user_data:
            params["UserData"] = user_data
        data = await self._ec2_request("RunInstances", params)
        instances = data.get("Instances", [{}])
        if instances:
            return self._parse_server(instances[0])
        raise Exception("No instance created")

    async def delete_server(self, server_id: str) -> bool:
        await self._ec2_request("TerminateInstances", {
            "InstanceId.1": server_id,
        })
        return True

    async def get_server(self, server_id: str) -> Optional[VPSServer]:
        try:
            data = await self._ec2_request("DescribeInstances", {
                "InstanceId.1": server_id,
            })
            for r in data.get("Reservations", []):
                for inst in r.get("Instances", []):
                    return self._parse_server(inst)
            return None
        except Exception:
            return None

    async def start_server(self, server_id: str) -> bool:
        await self._ec2_request("StartInstances", {"InstanceId.1": server_id})
        return True

    async def stop_server(self, server_id: str) -> bool:
        await self._ec2_request("StopInstances", {"InstanceId.1": server_id})
        return True

    async def reboot_server(self, server_id: str) -> bool:
        await self._ec2_request("RebootInstances", {"InstanceId.1": server_id})
        return True

    async def _ec2_request(self, action: str, params: Dict = None) -> Dict:
        """Make EC2 API request (simplified — real impl needs SigV4 signing)"""
        all_params = {"Action": action, "Version": "2016-11-15"}
        if params:
            all_params.update(params)
        logger.info("AWS EC2 %s: %s", action, params)
        # Real implementation: boto3.client('ec2').describe_instances(...)
        return {"Reservations": [], "Instances": []}

    def _parse_server(self, inst: Dict) -> VPSServer:
        state = inst.get("State", {}).get("Name", "")
        status_map = {
            "running": ServerStatus.RUNNING,
            "stopped": ServerStatus.STOPPED,
            "pending": ServerStatus.PROVISIONING,
            "stopping": ServerStatus.PROVISIONING,
            "shutting-down": ServerStatus.DELETING,
            "terminated": ServerStatus.DELETING,
        }
        return VPSServer(
            provider=CloudProvider.AWS,
            server_id=inst.get("InstanceId", ""),
            name=next(
                (t["Value"] for t in inst.get("Tags", [])
                 if t["Key"] == "Name"), ""
            ),
            status=status_map.get(state, ServerStatus.UNKNOWN),
            ip_address=inst.get("PublicIpAddress", ""),
            public_ipv4=inst.get("PublicIpAddress", ""),
            private_ipv4=inst.get("PrivateIpAddress", ""),
            region=inst.get("Placement", {}).get("AvailabilityZone", ""),
            os_image=inst.get("ImageId", ""),
            created_at=str(inst.get("LaunchTime", "")),
        )
