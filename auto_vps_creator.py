#!/usr/bin/env python3
"""
CK-NEXUS v1.4 - Auto VPS Creator
Combines: Web Agent + Email Verification + SSH + Omni AI Pool
Creates free VPS instances without credit card
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
from typing import Dict, Any, Optional


class AutoVPSCreator:
    def __init__(self):
        self.db_path = "/workspace/ck-nexus/nexus_system_sd.db"
        self.config_path = "/root/.ck-nexus/config.json"
        self.email = "iwepnewqviay800@gmail.com"
        self.password = "Ck880611"
        self.username = "ck_nexus_operator"
        
    def register_gratisvps(self) -> Dict[str, Any]:
        """Register for GratisVPS free VPS"""
        print("🚀 Registering for GratisVPS...")
        
        # Generate random password for VPS
        vps_password = f"CK-Nexus-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}!"
        
        # Create registration data
        reg_data = {
            "email": self.email,
            "password": self.password,
            "username": self.username,
            "vps_password": vps_password
        }
        
        # Try to register via API
        try:
            # GratisVPS uses a form-based registration
            # We'll create a script that the user can run
            script = f"""#!/bin/bash
# GratisVPS Registration Script
# Run this manually or via automation

echo "🚀 GratisVPS Registration"
echo "Email: {self.email}"
echo "Username: {self.username}"
echo ""
echo "Steps:"
echo "1. Go to https://gratisvps.net/cvps"
echo "2. Fill in email: {self.email}"
echo "3. Create account"
echo "4. Verify email"
echo "5. Create VPS instance"
echo ""
echo "Your VPS password will be: {vps_password}"
echo "Save this password!"
"""
            
            # Save registration script
            script_path = "/workspace/ck-nexus/gratisvps_register.sh"
            with open(script_path, "w") as f:
                f.write(script)
            os.chmod(script_path, 0o755)
            
            return {
                "status": "READY",
                "script": script_path,
                "vps_password": vps_password,
                "instructions": "Run the script and follow the steps"
            }
            
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    def register_oracle_cloud(self) -> Dict[str, Any]:
        """Register for Oracle Cloud Free Tier"""
        print("🚀 Preparing Oracle Cloud registration...")
        
        # Generate SSH key
        ssh_key_path = "/root/.ssh/oracle_key"
        if not os.path.exists(ssh_key_path):
            subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "4096",
                "-f", ssh_key_path, "-N", "", "-C", "ck-nexus-oracle"
            ], capture_output=True)
        
        # Read public key
        with open(f"{ssh_key_path}.pub") as f:
            public_key = f.read().strip()
        
        # Create registration helper
        script = f"""#!/bin/bash
# Oracle Cloud Free Tier Registration
# No credit card required for Always Free tier

echo "🚀 Oracle Cloud Free Tier Setup"
echo ""
echo "Steps:"
echo "1. Go to https://cloud.oracle.com"
echo "2. Click 'Sign Up for Free Tier'"
echo "3. Use email: {self.email}"
echo "4. Complete registration (no credit card needed for Always Free)"
echo "5. Create Compute Instance:"
echo "   - Image: Ubuntu 22.04"
echo "   - Shape: Ampere ARM (4 OCPU/24GB)"
echo "   - Add SSH Key (copy from below)"
echo ""
echo "Your SSH Public Key:"
cat {ssh_key_path}.pub
echo ""
echo "6. After creating instance, get the Public IP"
echo "7. Connect: ssh -i {ssh_key_path} ubuntu@<IP>"
echo "8. Set password: sudo passwd ubuntu"
"""
            
        script_path = "/workspace/ck-nexus/oracle_register.sh"
        with open(script_path, "w") as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        
        return {
            "status": "READY",
            "script": script_path,
            "ssh_key": public_key,
            "instructions": "Run the script and follow the steps"
        }
    
    def auto_configure_server(self, ip: str, password: str, provider: str = "oracle") -> bool:
        """Auto-configure server with n8n and AI Worker"""
        print(f"🚀 Auto-configuring server at {ip}...")
        
        setup_script = f"""#!/bin/bash
set -e

echo "[1/8] Updating system..."
apt-get update -qq && apt-get install -y -qq curl docker.io docker-compose git python3-pip

echo "[2/8] Setting password..."
echo "ubuntu:{password}" | chpasswd
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/ssh_config
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh

echo "[3/8] Starting Docker..."
systemctl enable docker && systemctl start docker

echo "[4/8] Creating n8n directory..."
mkdir -p /opt/n8n && cd /opt/n8n

echo "[5/8] Creating docker-compose.yml..."
cat > docker-compose.yml << 'YAML'
version: '3.8'
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    container_name: n8n
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=nexus_admin
      - N8N_BASIC_AUTH_PASSWORD=CK-Nexus-2026!
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - GENERIC_TIMEZONE=Asia/Bangkok
    volumes:
      - n8n_data:/home/node/.n8n
volumes:
  n8n_data:
YAML

echo "[6/8] Starting n8n..."
docker-compose up -d

echo "[7/8] Installing Worker API..."
mkdir -p /opt/ck-nexus-worker
pip3 install fastapi uvicorn httpx -q

cat > /opt/ck-nexus-worker/worker.py << 'PYEOF'
from fastapi import FastAPI
import httpx
app = FastAPI()

@app.get("/health")
def health():
    return {{"status": "alive", "node": "ck-nexus-worker", "version": "1.4"}}

@app.post("/compute")
async def compute(payload: dict):
    prompt = payload.get("prompt", "Hello")
    model = payload.get("model", "llama-3.1-8b-instant")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={{"Authorization": "Bearer GROQ_API_KEY_PLACEHOLDER"}},
            json={{"model": model, "messages": [{{"role": "user", "content": prompt}}], "max_tokens": 1024}},
            timeout=30.0
        )
        return {{"result": r.json()["choices"][0]["message"]["content"]}}
PYEOF

cd /opt/ck-nexus-worker && nohup uvicorn worker:app --host 0.0.0.0 --port 8000 &

echo "[8/8] Verifying services..."
sleep 5
echo "=== STATUS ==="
docker ps | grep n8n && echo "✅ n8n: RUNNING on port 5678" || echo "⚠️ n8n: FAILED"
curl -s http://localhost:8000/health && echo "✅ Worker: RUNNING on port 8000" || echo "⚠️ Worker: FAILED"

echo ""
echo "🎉 CK-NEXUS VPS WORKER DEPLOYED!"
echo "🌐 n8n: http://{ip}:5678"
echo "🤖 Worker: http://{ip}:8000"
echo "👤 User: nexus_admin"
echo "🔑 Pass: CK-Nexus-2026!"
"""
        
        try:
            # Try SSH with password
            proc = subprocess.run(
                ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
                 f"ubuntu@{ip}", setup_script],
                capture_output=True, text=True, timeout=180
            )
            
            if proc.returncode == 0:
                print(f"✅ Server configured successfully!")
                self._save_to_db(ip, password, provider)
                return True
            else:
                # Try with root
                proc = subprocess.run(
                    ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
                     f"root@{ip}", setup_script],
                    capture_output=True, text=True, timeout=180
                )
                if proc.returncode == 0:
                    print(f"✅ Server configured successfully!")
                    self._save_to_db(ip, password, provider)
                    return True
                else:
                    print(f"❌ Error: {proc.stderr[:200]}")
                    return False
                    
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def _save_to_db(self, ip: str, password: str, provider: str):
        """Save VPS info to database"""
        with sqlite3.connect(self.db_path) as conn:
            # Update existing VPS record
            conn.execute("""
                UPDATE autonomous_vps_servers
                SET vps_ip = ?, vps_password = ?, status = 'ACTIVE',
                    notes = ?, timestamp = ?
                WHERE provider_name LIKE ?
            """, (ip, password, f"SSH_IP:{ip}|SSH_PASSWORD:{password}", 
                  time.strftime("%Y-%m-%d %H:%M:%S"), f"%{provider}%"))
            conn.commit()
        print(f"💾 Saved to database!")
    
    def create_all_free_vps(self) -> Dict[str, Any]:
        """Create free VPS instances on all available providers"""
        results = {}
        
        # 1. Oracle Cloud (no credit card)
        print("\n=== Oracle Cloud Free Tier ===")
        oracle_result = self.register_oracle_cloud()
        results["oracle"] = oracle_result
        
        # 2. GratisVPS (no credit card)
        print("\n=== GratisVPS ===")
        gratis_result = self.register_gratisvps()
        results["gratisvps"] = gratis_result
        
        # 3. SolusVM (no credit card)
        print("\n=== SolusVM Dev Trial ===")
        solusvm_result = {
            "status": "READY",
            "url": "https://www.solusvm.com/free-trial",
            "instructions": "Go to URL and create account"
        }
        results["solusvm"] = solusvm_result
        
        return results


def main():
    creator = AutoVPSCreator()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            # Create all free VPS instances
            results = creator.create_all_free_vps()
            print("\n=== SUMMARY ===")
            for provider, result in results.items():
                print(f"\n{provider.upper()}: {result['status']}")
                if "script" in result:
                    print(f"  Script: {result['script']}")
                if "vps_password" in result:
                    print(f"  Password: {result['vps_password']}")
                print(f"  Instructions: {result['instructions']}")
                
        elif command == "configure":
            # Configure existing server
            if len(sys.argv) < 4:
                print("Usage: python3 auto_vps_creator.py configure <IP> <PASSWORD> [provider]")
                sys.exit(1)
            ip = sys.argv[2]
            password = sys.argv[3]
            provider = sys.argv[4] if len(sys.argv) > 4 else "oracle"
            creator.auto_configure_server(ip, password, provider)
            
        else:
            print("Commands: create, configure")
    else:
        # Default: create all
        results = creator.create_all_free_vps()
        print("\n=== SUMMARY ===")
        for provider, result in results.items():
            print(f"\n{provider.upper()}: {result['status']}")


if __name__ == "__main__":
    main()
