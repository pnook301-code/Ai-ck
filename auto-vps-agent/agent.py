#!/usr/bin/env python3
"""
CK-NEXUS Auto-VPS Agent Engine
Scans free VPS providers, analyzes with AI, auto-registers
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List

SD_PATH = "/workspace/ck-nexus"
CONFIG_PATH = "/root/.ck-nexus/config.json"

# Free VPS Providers
FREE_VPS_PROVIDERS = [
    {"name": "Oracle Cloud", "url": "https://cloud.oracle.com/free_signup", "type": "always-free", "specs": "4 OCPU/24GB", "days": 365, "needs_card": False},
    {"name": "GratisVPS", "url": "https://gratisvps.net/cvps", "type": "free", "specs": "2GB/2CPU", "days": -1, "needs_card": False},
    {"name": "SolusVM", "url": "https://www.solusvm.com/free-trial", "type": "trial", "specs": "Sandbox", "days": 30, "needs_card": False},
    {"name": "Google Cloud", "url": "https://console.cloud.google.com/billing/free", "type": "free-tier", "specs": "$300 credit", "days": 90, "needs_card": True},
    {"name": "Kamatera", "url": "https://www.kamatera.com/free-trial/", "type": "trial", "specs": "4CPU/8GB", "days": 30, "needs_card": False},
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


async def analyze_with_ai(text: str) -> Dict[str, Any]:
    """Use OpenRouter AI to analyze VPS offers"""
    config = load_config()
    openrouter_key = config.get("openrouter", {}).get("key", "")

    prompt = f"""คุณคือ AI นักวิเคราะห์ VPS ฟรี
วิเคราะห์ข้อความนี้: "{text[:1500]}"

ตอบกลับเป็น JSON เท่านั้น:
{{"isFreeVPS": true/false, "trustScore": 1-10, "reason": "เหตุผลสั้นๆ", "recommended": true/false}}"""

    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps({
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.3
            }).encode(),
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"  ⚠️ AI error: {e}")
    return {"isFreeVPS": False, "trustScore": 0, "reason": "AI failed", "recommended": False}


def save_to_db(provider_name: str, ip: str = "", password: str = "", status: str = "AWAITING"):
    db_path = os.path.join(SD_PATH, "nexus_system_sd.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            UPDATE autonomous_vps_servers 
            SET vps_ip=?, vps_password=?, status=?, notes=?, timestamp=datetime('now')
            WHERE provider_name LIKE ?
        """, (ip, password, status, f"SSH_IP:{ip}|SSH_PASSWORD:{password}", f"%{provider_name}%"))
        conn.commit()
    print(f"  💾 Saved to DB: {provider_name}")


def scan_providers():
    """Scan all free VPS providers"""
    print("╔══════════════════════════════════════════════╗")
    print("║  🤖 CK-NEXUS AUTO-VPS AGENT ENGINE          ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  🧠 AI: Groq Llama 3.3 70B                  ║")
    print("║  🎯 Target: Free VPS Providers               ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    results = []

    for provider in FREE_VPS_PROVIDERS:
        print(f"\n🔍 Scanning: {provider['name']}")
        print(f"   URL: {provider['url']}")
        print(f"   Type: {provider['type']} | Days: {provider['days']} | Card: {'Yes' if provider['needs_card'] else 'No'}")

        # Try to fetch page
        try:
            req = urllib.request.Request(provider['url'], headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode(errors='ignore')[:3000]

                # Analyze with AI
                import asyncio
                analysis = asyncio.run(analyze_with_ai(content))

                if analysis.get('recommended', False) or analysis.get('trustScore', 0) >= 7:
                    print(f"   ✅ AI Approved: {analysis.get('reason', '')} (Score: {analysis.get('trustScore', 0)})")
                    save_to_db(provider['name'], status="READY_FOR_REGISTRATION")
                    results.append({"provider": provider['name'], "status": "APPROVED", "analysis": analysis})
                else:
                    print(f"   ❌ AI Rejected: {analysis.get('reason', '')}")
                    results.append({"provider": provider['name'], "status": "REJECTED", "analysis": analysis})
        except Exception as e:
            print(f"   ⚠️ Fetch error: {e}")
            results.append({"provider": provider['name'], "status": "ERROR", "error": str(e)})

    return results


def generate_registration_scripts():
    """Generate registration scripts for each provider"""
    print("\n📋 Generating registration scripts...")

    # Oracle Cloud
    oracle_script = f"""#!/bin/bash
# Oracle Cloud Free Tier Registration
# No credit card required for Always Free tier

echo "=== Oracle Cloud Free Tier Setup ==="
echo ""
echo "1. Go to: https://cloud.oracle.com"
echo "2. Click 'Sign Up for Free Tier'"
echo "3. Use email: iwepnewqviay800@gmail.com"
echo "4. Complete registration"
echo "5. Create Compute Instance:"
echo "   - Image: Ubuntu 22.04"
echo "   - Shape: Ampere ARM (4 OCPU/24GB)"
echo ""
echo "6. SSH Public Key:"
cat /root/.ssh/oracle_key.pub
echo ""
echo "7. After creating instance, get Public IP"
echo "8. Connect: ssh -i /root/.ssh/oracle_key ubuntu@<IP>"
echo "9. Set password: sudo passwd ubuntu"
echo ""
echo "10. Send to Telegram: add vps oracle <IP> <Password>"
"""
    with open(os.path.join(SD_PATH, "oracle_register.sh"), "w") as f:
        f.write(oracle_script)
    os.chmod(os.path.join(SD_PATH, "oracle_register.sh"), 0o755)

    # GratisVPS
    gratis_script = """#!/bin/bash
# GratisVPS Registration - No Credit Card Required

echo "=== GratisVPS Setup ==="
echo ""
echo "1. Go to: https://gratisvps.net/cvps"
echo "2. Fill in email: iwepnewqviay800@gmail.com"
echo "3. Create password: CK-Nexus-2026!"
echo "4. Complete registration"
echo "5. Deploy free VPS instance"
echo ""
echo "6. Send to Telegram: add vps gratisvps <IP> <Password>"
"""
    with open(os.path.join(SD_PATH, "gratisvps_register.sh"), "w") as f:
        f.write(gratis_script)
    os.chmod(os.path.join(SD_PATH, "gratisvps_register.sh"), 0o755)

    # SolusVM
    solusvm_script = """#!/bin/bash
# SolusVM Developer Trial - No Credit Card Required

echo "=== SolusVM Dev Trial Setup ==="
echo ""
echo "1. Go to: https://www.solusvm.com/free-trial"
echo "2. Fill in registration form"
echo "3. Use email: iwepnewqviay800@gmail.com"
echo "4. Complete registration"
echo "5. Deploy trial VPS instance"
echo ""
echo "6. Send to Telegram: add vps solusvm <IP> <Password>"
"""
    with open(os.path.join(SD_PATH, "solusvm_register.sh"), "w") as f:
        f.write(solusvm_script)
    os.chmod(os.path.join(SD_PATH, "solusvm_register.sh"), 0o755)

    print("  ✅ oracle_register.sh")
    print("  ✅ gratisvps_register.sh")
    print("  ✅ solusvm_register.sh")


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "scan":
            results = scan_providers()
            print("\n" + "=" * 50)
            print("📊 SCAN RESULTS:")
            print("=" * 50)
            for r in results:
                status = "✅" if r["status"] == "APPROVED" else "❌"
                print(f"  {status} {r['provider']}: {r['status']}")

        elif cmd == "scripts":
            generate_registration_scripts()

        elif cmd == "configure":
            if len(sys.argv) < 4:
                print("Usage: python3 agent.py configure <IP> <PASSWORD> [provider]")
                sys.exit(1)
            ip = sys.argv[2]
            password = sys.argv[3]
            provider = sys.argv[4] if len(sys.argv) > 4 else "oracle"
            save_to_db(provider, ip, password, "ACTIVE")
            print(f"✅ VPS {provider} configured at {ip}")

        elif cmd == "all":
            generate_registration_scripts()
            results = scan_providers()
            print("\n✅ Auto-VPS Agent complete!")
            print("📋 Registration scripts saved to:", SD_PATH)

        else:
            print("Commands: scan, scripts, configure, all")
    else:
        generate_registration_scripts()
        results = scan_providers()
        print("\n✅ Auto-VPS Agent complete!")


if __name__ == "__main__":
    main()
