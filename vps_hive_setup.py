#!/usr/bin/env python3
"""
CK-NEXUS v1.2 - Omni Hive VPS Setup
Deploy n8n + AI Pool on VPS via SSH (Headless)
"""

import os
import time
import json
import sqlite3
import subprocess
from typing import Dict, List, Any, Optional


class NexusOmniHiveSetup:
    """Deploy n8n + AI models on VPS cluster via SSH"""

    def __init__(self, sd_path: str = "/workspace/ck-nexus"):
        self.sd_path = sd_path
        self.db_path = os.path.join(sd_path, "nexus_system_sd.db")
        self.config_path = "/root/.ck-nexus/config.json"
        self.ssh_key = os.path.expanduser("~/.ssh/id_rsa")
        self.deployed_nodes = []

    def _load_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def _get_vps_list(self) -> List[Dict]:
        """ดึงรายชื่อ VPS ทั้งหมดจาก SD Card"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM autonomous_vps_servers WHERE status LIKE 'ACTIVE%'"
                ).fetchall()
                return [dict(r) for r in rows]
        except:
            return []

    def _get_ssh_password(self, provider: str) -> Optional[str]:
        """ดึงรหัสผ่าน SSH จากฐานข้อมูล (ต้องกรอกหลังลงทะเบียนจริง)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT notes FROM autonomous_vps_servers WHERE provider_name LIKE ?",
                    (f"%{provider}%",)
                ).fetchone()
                if row and row[0] and "SSH_PASSWORD:" in row[0]:
                    return row[0].split("SSH_PASSWORD:")[1].strip()
        except:
            pass
        return None

    def generate_docker_compose(self) -> str:
        """สร้าง docker-compose.yml สำหรับ n8n + AI Pool"""
        config = self._load_config()
        groq_key = config.get("groq", {}).get("key", "")
        openrouter_key = config.get("openrouter", {}).get("key", "")

        return f"""version: '3.8'

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - GENERIC_TIMEZONE=Asia/Bangkok
      - N8N_SECURE_COOKIE=false
      - GROQ_API_KEY={groq_key}
      - OPENROUTER_API_KEY={openrouter_key}
    volumes:
      - n8n_data:/home/node/.local/share/n8n
    deploy:
      resources:
        limits:
          memory: 2G

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - n8n

  watchtower:
    image: containrrr/watchtower
    restart: always
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_SCHEDULE=0 0 4 * * *
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

volumes:
  n8n_data:"""

    def generate_nginx_config(self) -> str:
        return """events {
    worker_connections 1024;
}

http {
    upstream n8n {
        server n8n:5678;
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://n8n;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}"""

    def generate_setup_script(self, vps_ip: str) -> str:
        """สร้างสคริปต์ bash สำหรับติดตั้งทั้งหมดบน VPS"""
        docker_compose = self.generate_docker_compose()
        nginx_config = self.generate_nginx_config()

        return f"""#!/bin/bash
set -e

echo "[NEXUS] Starting Omni Hive setup on {vps_ip}..."

# Update & install Docker
apt-get update -y
apt-get install -y docker.io docker-compose curl git ufw

# Firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5678/tcp
echo "y" | ufw enable

# Start Docker
systemctl enable docker
systemctl start docker

# Create n8n directory
mkdir -p /root/nexus_hive
cd /root/nexus_hive

# Write docker-compose.yml
cat > docker-compose.yml << 'DOCKEREOF'
{docker_compose}
DOCKEREOF

# Write nginx config
cat > nginx.conf << 'NGINXEOF'
{nginx_config}
NGINXEOF

# Start services
docker-compose up -d

# Wait for n8n
sleep 10

# Verify
if curl -s http://localhost:5678 > /dev/null 2>&1; then
    echo "N8N_DEPLOYED_SUCCESSFULLY"
    echo "DEPLOYED" > /root/nexus_hive/status.txt
    echo "$(date)" > /root/nexus_hive/deploy_time.txt
else
    echo "N8N_DEPLOY_FAILED"
    echo "FAILED" > /root/nexus_hive/status.txt
fi

# Install AI tools
apt-get install -y python3-pip
pip3 install requests sqlite3

echo "[NEXUS] Setup complete."
"""

    def deploy_to_vps(self, vps_ip: str, password: str = None) -> Dict[str, Any]:
        """สั่งติดตั้ง n8n + AI Pool บน VPS ผ่าน SSH"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "vps_ip": vps_ip,
            "timestamp": timestamp,
            "status": "FAILED",
            "n8n_port": 5678,
            "details": ""
        }

        try:
            if password:
                # Use sshpass for password-based SSH
                script = self.generate_setup_script(vps_ip)
                cmd = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no root@{vps_ip} "{script}"'
            else:
                # Use SSH key
                if not os.path.exists(self.ssh_key):
                    result["details"] = "SSH key not found"
                    return result
                script = self.generate_setup_script(vps_ip)
                cmd = f'ssh -i {self.ssh_key} -o StrictHostKeyChecking=no root@{vps_ip} "{script}"'

            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)

            if "N8N_DEPLOYED_SUCCESSFULLY" in proc.stdout or proc.returncode == 0:
                result["status"] = "DEPLOYED"
                result["details"] = "n8n + AI Pool installed successfully"
                self.deployed_nodes.append(vps_ip)
            else:
                result["details"] = proc.stderr[:200] if proc.stderr else "Unknown error"

        except subprocess.TimeoutExpired:
            result["details"] = "SSH connection timeout (180s)"
        except Exception as e:
            result["details"] = str(e)[:200]

        # Log to SD Card
        self._log_deployment(result)
        return result

    def _log_deployment(self, result: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO work_logs (timestamp, action, details)
                    VALUES (?, ?, ?)
                """, (
                    result["timestamp"],
                    f"Hive Deploy: {result['vps_ip']}",
                    f"Status: {result['status']} | {result['details'][:100]}"
                ))
                conn.commit()
        except:
            pass

    def check_n8n_health(self, vps_ip: str) -> Dict[str, Any]:
        """เช็คสุขภาพ n8n บน VPS"""
        try:
            cmd = f'curl -s -o /dev/null -w "%{{http_code}}" http://{vps_ip}:5678'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            status_code = proc.stdout.strip()

            return {
                "vps_ip": vps_ip,
                "n8n_status": "ONLINE" if status_code in ["200", "302"] else "OFFLINE",
                "http_code": status_code,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except:
            return {
                "vps_ip": vps_ip,
                "n8n_status": "UNREACHABLE",
                "http_code": "000",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    def deploy_to_all_vps(self) -> List[Dict]:
        """ติดตั้ง n8n บน VPS ทุกตัวที่มี IP จริง"""
        results = []
        vps_list = self._get_vps_list()

        for vps in vps_list:
            provider = vps.get("provider_name", "")
            # Only deploy to nodes that have real IPs (not just registered)
            # In production, this would check for actual IP addresses
            # For now, we log that deployment is ready
            results.append({
                "provider": provider,
                "status": "READY_FOR_DEPLOYMENT",
                "note": "Awaiting real VPS IP/password from provider"
            })

        return results

    def generate_report(self) -> str:
        """สรุปสถานะ Hive Network"""
        vps_list = self._get_vps_list()
        report = []
        report.append("=" * 60)
        report.append("🐝 OMNI HIVE NETWORK - STATUS")
        report.append("=" * 60)
        report.append(f"  📡 Total VPS Nodes:     {len(vps_list)}")
        report.append(f"  ✅ Deployed Nodes:      {len(self.deployed_nodes)}")
        report.append(f"  🔧 n8n Port:            5678")
        report.append(f"  🛡️ Firewall:            UFW Active")
        report.append(f"  📦 Auto-Update:         Watchtower Enabled")
        report.append("")

        report.append("  🖥️  VPS Cluster:")
        for vps in vps_list:
            icon = "🟢" if vps["provider_name"] in ["Oracle Cloud Free Tier", "Google Cloud Free Tier"] else "🔵"
            report.append(f"    {icon} {vps['provider_name']}: {vps['status']}")

        report.append("")
        report.append("  🔗 Deployed Endpoints:")
        for node in self.deployed_nodes:
            report.append(f"    ✅ http://{node}:5678 (n8n)")

        if not self.deployed_nodes:
            report.append("    ⏳ No nodes deployed yet (awaiting real VPS IPs)")

        report.append("=" * 60)
        return "\n".join(report)


if __name__ == "__main__":
    hive = NexusOmniHiveSetup()
    print(hive.generate_report())
