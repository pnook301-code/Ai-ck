"""Cloud types — provider enums, VPS plans, server state, credentials"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time
import uuid


class CloudProvider(Enum):
    HETZNER = "hetzner"
    DIGITALOCEAN = "digitalocean"
    AWS = "aws"
    GCP = "gcp"
    ORACLE = "oracle"


class ServerStatus(Enum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    STOPPED = "stopped"
    REBOOTING = "rebooting"
    DELETING = "deleting"
    ERROR = "error"
    UNKNOWN = "unknown"


class Region(Enum):
    # Hetzner
    HETZNER_FSN1 = "fsn1"
    HETZNER_NBG1 = "nbg1"
    HETZNER_HEL1 = "hel1"
    # DigitalOcean
    DO_NYC = "nyc3"
    DO_SFO = "sfo3"
    DO_LON = "lon1"
    DO_SGP = "sgp1"
    DO_FRA = "fra1"
    # AWS
    AWS_US_EAST_1 = "us-east-1"
    AWS_US_WEST_2 = "us-west-2"
    AWS_EU_WEST_1 = "eu-west-1"
    AWS_AP_SOUTH_1 = "ap-south-1"
    # GCP
    GCP_US_CENTRAL1 = "us-central1"
    GCP_EU_WEST1 = "europe-west1"
    GCP_ASIA_EAST1 = "asia-east1"
    # Oracle (always free regions)
    ORACLE_US_ASHBURN = "us-ashburn-1"
    ORACLE_US_PHOENIX = "us-phoenix-1"
    ORACLE_DE_FRANKFURT = "eu-frankfurt-1"
    ORACLE_US_SAN_JOSE = "us-sanjose-1"


@dataclass
class CloudCredentials:
    provider: CloudProvider
    api_key: str = ""
    api_secret: str = ""
    project_id: str = ""
    fingerprint: str = ""
    private_key_path: str = ""
    region: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        if self.provider == CloudProvider.HETZNER:
            return bool(self.api_key)
        if self.provider == CloudProvider.DIGITALOCEAN:
            return bool(self.api_key)
        if self.provider == CloudProvider.AWS:
            return bool(self.api_key and self.api_secret)
        if self.provider == CloudProvider.GCP:
            return bool(self.project_id and self.private_key_path)
        if self.provider == CloudProvider.ORACLE:
            return bool(self.fingerprint and self.private_key_path)
        return False


@dataclass
class VPSPlan:
    provider: CloudProvider
    plan_id: str
    name: str
    vcpus: int
    ram_gb: float
    disk_gb: int
    bandwidth_tb: float
    price_monthly_usd: float
    is_free_tier: bool = False
    region: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "plan_id": self.plan_id,
            "name": self.name,
            "vcpus": self.vcpus,
            "ram_gb": self.ram_gb,
            "disk_gb": self.disk_gb,
            "bandwidth_tb": self.bandwidth_tb,
            "price_monthly_usd": self.price_monthly_usd,
            "is_free_tier": self.is_free_tier,
            "region": self.region,
        }


@dataclass
class VPSServer:
    provider: CloudProvider
    server_id: str
    name: str
    status: ServerStatus
    ip_address: str = ""
    public_ipv4: str = ""
    private_ipv4: str = ""
    ipv6: str = ""
    plan: Optional[VPSPlan] = None
    region: str = ""
    os_image: str = "ubuntu-22.04"
    ssh_key_name: str = ""
    created_at: float = field(default_factory=time.time)
    password: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def ssh_command(self) -> str:
        ip = self.public_ipv4 or self.ip_address
        return f"root@{ip}" if ip else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "server_id": self.server_id,
            "name": self.name,
            "status": self.status.value,
            "ip_address": self.ip_address,
            "public_ipv4": self.public_ipv4,
            "private_ipv4": self.private_ipv4,
            "ipv6": self.ipv6,
            "plan": self.plan.to_dict() if self.plan else None,
            "region": self.region,
            "os_image": self.os_image,
            "created_at": self.created_at,
        }


@dataclass
class CloudOperation:
    id: str = field(default_factory=lambda: f"op_{uuid.uuid4().hex[:12]}")
    provider: CloudProvider = CloudProvider.HETZNER
    operation: str = ""
    status: str = "pending"
    server: Optional[VPSServer] = None
    error: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    logs: List[str] = field(default_factory=list)

    def complete(self, server: VPSServer = None):
        self.status = "completed"
        self.server = server
        self.completed_at = time.time()

    def fail(self, error: str):
        self.status = "failed"
        self.error = error
        self.completed_at = time.time()

    @property
    def duration_seconds(self) -> float:
        end = self.completed_at or time.time()
        return end - self.started_at


# Pre-defined free tier plans
FREE_TIER_PLANS = {
    CloudProvider.ORACLE: VPSPlan(
        provider=CloudProvider.ORACLE,
        plan_id="VM.Standard.E2.1.Micro",
        name="Always Free Micro",
        vcpus=1, ram_gb=1.0, disk_gb=50, bandwidth_tb=10,
        price_monthly_usd=0.0, is_free_tier=True,
    ),
    CloudProvider.HETZNER: VPSPlan(
        provider=CloudProvider.HETZNER,
        plan_id="cx22",
        name="CX22 (Cheapest)",
        vcpus=2, ram_gb=4.0, disk_gb=40, bandwidth_tb=20,
        price_monthly_usd=3.49, is_free_tier=False,
    ),
    CloudProvider.DIGITALOCEAN: VPSPlan(
        provider=CloudProvider.DIGITALOCEAN,
        plan_id="s-1vcpu-1gb",
        name="Basic $6/mo",
        vcpus=1, ram_gb=1.0, disk_gb=25, bandwidth_tb=1,
        price_monthly_usd=6.0, is_free_tier=False,
    ),
    CloudProvider.GCP: VPSPlan(
        provider=CloudProvider.GCP,
        plan_id="e2-micro",
        name="Always Free e2-micro",
        vcpus=2, ram_gb=1.0, disk_gb=30, bandwidth_tb=1,
        price_monthly_usd=0.0, is_free_tier=True,
    ),
    CloudProvider.AWS: VPSPlan(
        provider=CloudProvider.AWS,
        plan_id="t2.micro",
        name="Free Tier t2.micro (12mo)",
        vcpus=1, ram_gb=1.0, disk_gb=30, bandwidth_tb=1,
        price_monthly_usd=0.0, is_free_tier=True,
    ),
}

DEFAULT_SSH_KEY_NAME = "ck-nexus-deploy"
DEFAULT_OS_IMAGE = {
    CloudProvider.HETZNER: "ubuntu-22.04",
    CloudProvider.DIGITALOCEAN: "ubuntu-22-04-x64",
    CloudProvider.AWS: "ami-0c02fb55956c7d316",
    CloudProvider.GCP: "ubuntu-2204-lts",
    CloudProvider.ORACLE: "Oracle-Linux-8.5-Gen2-Micro",
}

INSTALL_SCRIPT_URL = "https://raw.githubusercontent.com/pnook301-code/Ai-ck/main/deploy/install_on_vps.sh"
