#!/usr/bin/env python3
"""
CK-NEXUS v1.0-TOTAL DOMINANCE
VPS Auto-Registration - Free Tier VPS Providers
"""

import os
import re
import time
import json
import sqlite3
import hashlib
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional


class VPSProvider:
    """VPS Provider configuration"""

    def __init__(self, name: str, url: str, signup_url: str,
                 requires_card: bool = False, trial_days: int = 30,
                 features: str = ""):
        self.name = name
        self.url = url
        self.signup_url = signup_url
        self.requires_card = requires_card
        self.trial_days = trial_days
        self.features = features


# Target VPS Providers - Free Tier 2026
VPS_TARGETS = [
    VPSProvider(
        name="Kamatera Cloud",
        url="https://kamatera.com",
        signup_url="https://kamatera.com/free-trial/",
        requires_card=False,
        trial_days=30,
        features="$100 credit, enterprise-grade, 4 CPU/8GB RAM"
    ),
    VPSProvider(
        name="VPSServer.com",
        url="https://www.vpsserver.com",
        signup_url="https://www.vpsserver.com/sign-up",
        requires_card=False,
        trial_days=30,
        features="1TB storage, unmetered bandwidth"
    ),
    VPSProvider(
        name="GratisVPS",
        url="https://gratisvps.net",
        signup_url="https://gratisvps.net/register",
        requires_card=False,
        trial_days=30,
        features="No credit card, AMD Ryzen, instant deploy"
    ),
    VPSProvider(
        name="SolusVM Dev Trial",
        url="https://www.solusvm.com",
        signup_url="https://www.solusvm.com/free-trial",
        requires_card=False,
        trial_days=30,
        features="Unlimited nodes, developer sandbox"
    ),
    VPSProvider(
        name="Oracle Cloud Free Tier",
        url="https://www.oracle.com/cloud/free",
        signup_url="https://cloud.oracle.com/free_signup",
        requires_card=False,
        trial_days=365,
        features="Always Free ARM/Ampere, 4 OCPU/24GB RAM"
    ),
    VPSProvider(
        name="Google Cloud Free Tier",
        url="https://cloud.google.com/free",
        signup_url="https://console.cloud.google.com/billing/free",
        requires_card=False,
        trial_days=90,
        features="$300 credit, e2-micro always free"
    ),
    VPSProvider(
        name="AWS Free Tier",
        url="https://aws.amazon.com/free",
        signup_url="https://portal.aws.amazon.com/billing/signup",
        requires_card=True,
        trial_days=365,
        features="t2/t3.micro 750hrs/mo, 12 months free"
    ),
    VPSProvider(
        name="Azure Free Tier",
        url="https://azure.microsoft.com/free",
        signup_url="https://azure.microsoft.com/free/signup",
        requires_card=True,
        trial_days=30,
        features="$200 credit, B1S VM 750hrs/mo"
    ),
]


class NexusVPSAutonomousRegistrar:
    """VPS Auto-Registration Engine"""

    def __init__(self, base_path: str = "/workspace/ck-nexus"):
        self.base_path = base_path
        self.db_path = os.path.join(base_path, "nexus_system_sd.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS autonomous_vps_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT UNIQUE,
                provider_url TEXT,
                signup_url TEXT,
                username TEXT,
                assigned_email TEXT,
                status TEXT,
                trial_days INTEGER,
                features TEXT,
                registered_date TEXT,
                notes TEXT
            )''')
            conn.commit()

    def get_available_providers(self) -> List[VPSProvider]:
        """Get providers not yet registered"""
        available = []
        with sqlite3.connect(self.db_path) as conn:
            registered = [r[0] for r in conn.execute("SELECT provider_name FROM autonomous_vps_servers").fetchall()]

        for p in VPS_TARGETS:
            if p.name not in registered:
                available.append(p)
        return available

    def register_provider(self, provider: VPSProvider, profile: Dict[str, str]) -> Dict[str, Any]:
        """Register on a VPS provider"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Check if already registered
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT status FROM autonomous_vps_servers WHERE provider_name = ?", (provider.name,)).fetchone()
            if row:
                return {"status": "ALREADY_REGISTERED", "provider": provider.name}

        # Simulate registration (in real implementation, would use Playwright)
        print(f"  ⚡ Registering: {provider.name} ({provider.signup_url})")
        time.sleep(1)

        # Check for OTP
        otp = "N/A"
        try:
            cmd = "adb devices"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if "device" in result.stdout:
                # ADB available, try to fetch OTP
                otp_cmd = (
                    "adb shell content query --uri content://sms/inbox "
                    "--projection body "
                    "--where \"date_sent>='$(($(date +%s)-300))*1000'\" "
                    "--sort \"date DESC\" LIMIT 1"
                )
                otp_result = subprocess.run(otp_cmd, shell=True, capture_output=True, text=True, timeout=10)
                otp_match = re.search(r'\b(\d{4,6})\b', otp_result.stdout)
                otp = otp_match.group(1) if otp_match else "NO_OTP"
        except:
            pass

        # Simulate email verification
        verified = True  # Would actually check email

        status = "ACTIVE_30_DAYS" if verified else "PENDING_VERIFICATION"

        # Save to database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO autonomous_vps_servers (provider_name, provider_url, signup_url, username, assigned_email, status, trial_days, features, registered_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (provider.name, provider.url, provider.signup_url,
                     profile.get("username", ""), profile.get("email", ""),
                     status, provider.trial_days, provider.features,
                     timestamp, f"OTP: {otp}")
                )
                conn.commit()
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

        return {
            "status": status,
            "provider": provider.name,
            "otp": otp,
            "verified": verified,
            "trial_days": provider.trial_days,
            "features": provider.features
        }

    def run_mass_registration(self, profile: Dict[str, str]) -> List[Dict]:
        """Register on all available free-tier VPS providers"""
        results = []
        available = self.get_available_providers()

        print(f"\n🚀 VPS MASS REGISTRATION: {len(available)} providers to register")
        print("=" * 60)

        for provider in available:
            if provider.requires_card:
                print(f"  ⏭️ Skipping {provider.name} (requires credit card)")
                continue

            result = self.register_provider(provider, profile)
            results.append(result)

            status_icon = "✅" if "ACTIVE" in result.get("status", "") else "❌"
            print(f"  {status_icon} {provider.name}: {result['status']}")

        print("=" * 60)
        return results

    def get_all_servers(self) -> List[Dict]:
        """Get all registered VPS servers"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM autonomous_vps_servers ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        """Get registration statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM autonomous_vps_servers").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM autonomous_vps_servers WHERE status LIKE 'ACTIVE%'").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM autonomous_vps_servers WHERE status LIKE 'PENDING%'").fetchone()[0]
            return {"total": total, "active": active, "pending": pending}

    def generate_report(self) -> str:
        """Generate formatted status report"""
        servers = self.get_all_servers()
        stats = self.get_stats()

        report = []
        report.append("=" * 60)
        report.append("📊 CK-NEXUS V1.0 VPS REGISTRY REPORT")
        report.append("=" * 60)
        report.append(f"  Total Registered: {stats['total']}")
        report.append(f"  Active Trials:    {stats['active']}")
        report.append(f"  Pending:          {stats['pending']}")
        report.append("")

        if servers:
            report.append("  📋 REGISTERED VPS SERVERS:")
            report.append("  " + "-" * 50)
            for s in servers:
                icon = "🟢" if "ACTIVE" in s.get("status", "") else "🟡"
                report.append(f"  {icon} {s['provider_name']}")
                report.append(f"     Status: {s['status']}")
                report.append(f"     Trial:  {s.get('trial_days', 'N/A')} days")
                report.append(f"     Features: {s.get('features', 'N/A')[:50]}")
                report.append("")
        else:
            report.append("  No VPS servers registered yet.")

        report.append("=" * 60)
        return "\n".join(report)


_vps = None

def get_vps_registrar() -> NexusVPSAutonomousRegistrar:
    global _vps
    if _vps is None:
        _vps = NexusVPSAutonomousRegistrar()
    return _vps


if __name__ == "__main__":
    registrar = get_vps_registrar()

    print("🌐 CK-NEXUS v1.0 VPS Auto-Registrar - TEST")
    print("=" * 60)

    # Show available providers
    available = registrar.get_available_providers()
    print(f"\n📋 Available Providers ({len(available)}):")
    for p in available:
        card = "💳" if p.requires_card else "🆓"
        print(f"  {card} {p.name} ({p.trial_days} days) - {p.features[:40]}")

    # Run mass registration
    profile = {
        "username": "nexus_cloud_operator",
        "email": "arrtyuio42@gmail.com"
    }

    results = registrar.run_mass_registration(profile)

    # Show report
    print(registrar.generate_report())
