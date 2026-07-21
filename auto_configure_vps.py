#!/usr/bin/env python3
"""
CK-NEXUS - Auto-configure Oracle Cloud VPS
Run: python3 auto_configure_vps.py <IP> <PASSWORD>
"""

import sys
import subprocess
import json
import sqlite3
import time


def configure_vps(ip, password):
    print(f"🚀 Configuring VPS at {ip}...")

    # Create setup script
    setup_script = """#!/bin/bash
set -e

echo "[1/8] Updating system..."
apt-get update -qq && apt-get install -y -qq curl docker.io docker-compose git python3-pip

echo "[2/8] Setting password for ubuntu..."
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
    return {"status": "alive", "node": "ck-nexus-worker", "version": "1.4"}

@app.post("/compute")
async def compute(payload: dict):
    prompt = payload.get("prompt", "Hello")
    model = payload.get("model", "llama-3.1-8b-instant")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer GROQ_API_KEY_PLACEHOLDER"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024},
            timeout=30.0
        )
        return {"result": r.json()["choices"][0]["message"]["content"]}
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
""".format(password=password, ip=ip)

    # Try SSH connection
    try:
        # First try with password
        proc = subprocess.run(
            ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
             f"ubuntu@{ip}", setup_script],
            capture_output=True, text=True, timeout=180
        )
        if proc.returncode == 0:
            print(f"✅ VPS configured successfully!")
            print(proc.stdout)
            return True
        else:
            print(f"⚠️ SSH with ubuntu failed, trying root...")
            proc = subprocess.run(
                ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
                 f"root@{ip}", setup_script],
                capture_output=True, text=True, timeout=180
            )
            if proc.returncode == 0:
                print(f"✅ VPS configured successfully!")
                print(proc.stdout)
                return True
            else:
                print(f"❌ Error: {proc.stderr}")
                return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def save_to_db(ip, password):
    """Save VPS info to database"""
    db_path = "/workspace/ck-nexus/nexus_system_sd.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            UPDATE autonomous_vps_servers
            SET vps_ip = ?, vps_password = ?, status = 'ACTIVE',
                notes = ?, timestamp = ?
            WHERE provider_name LIKE '%Oracle%'
        """, (ip, password, f"SSH_IP:{ip}|SSH_PASSWORD:{password}", time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    print(f"💾 Saved to database!")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 auto_configure_vps.py <IP> <PASSWORD>")
        sys.exit(1)

    ip = sys.argv[1]
    password = sys.argv[2]

    success = configure_vps(ip, password)
    if success:
        save_to_db(ip, password)
        print("\n🎉 All done! VPS is ready for CK-NEXUS.")
    else:
        print("\n⚠️ Setup incomplete. Check errors above.")
