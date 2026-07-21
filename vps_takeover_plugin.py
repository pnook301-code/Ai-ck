#!/usr/bin/env python3
"""
CK-NEXUS v1.0 - VPS Takeover Plugin
SSH auto-connect and remote control
"""

import os
import time
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional


class NexusVPSTakeoverPlugin:
    """VPS Takeover - SSH injection and remote control"""

    def __init__(self, base_path: str = "/workspace/ck-nexus"):
        self.base_path = base_path
        self.db_path = os.path.join(base_path, "nexus_system_sd.db")
        self.ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
        self.vps_nodes_path = os.path.join(base_path, "vps_nodes.json")
        self._key_checked = False

    def _ensure_ssh_key(self):
        """Generate SSH key if not exists (lazy - only when needed)"""
        if self._key_checked:
            return
        self._key_checked = True
        if not os.path.exists(self.ssh_key_path):
            os.makedirs(os.path.dirname(self.ssh_key_path), exist_ok=True)
            subprocess.run(
                f'ssh-keygen -t rsa -b 4096 -f {self.ssh_key_path} -N "" -q',
                shell=True, capture_output=True, timeout=30
            )
            print("  🔑 SSH key generated")

    def get_public_key(self) -> str:
        pub_path = f"{self.ssh_key_path}.pub"
        if os.path.exists(pub_path):
            with open(pub_path) as f:
                return f.read().strip()
        return ""

    def inject_key(self, ip: str, password: str, port: int = 22) -> bool:
        """Inject SSH key to remote VPS"""
        self._ensure_ssh_key()
        pub_key = self.get_public_key()
        if not pub_key:
            return False

        try:
            cmd = (
                f'sshpass -p "{password}" ssh-copy-id '
                f'-o StrictHostKeyChecking=no '
                f'-p {port} root@{ip}'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            return result.returncode == 0
        except:
            return False

    def execute_remote(self, ip: str, command: str, port: int = 22) -> Dict[str, Any]:
        """Execute command on remote VPS"""
        try:
            cmd = (
                f'ssh -i {self.ssh_key_path} '
                f'-o StrictHostKeyChecking=no '
                f'-o ConnectTimeout=10 '
                f'-p {port} root@{ip} '
                f'"{command}"'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def setup_vps(self, ip: str, password: str = None, port: int = 22) -> Dict[str, Any]:
        """Full VPS setup - inject key, install deps, configure"""
        print(f"  ⚡ Setting up VPS: {ip}")

        # Step 1: Inject SSH key
        if password:
            self.inject_key(ip, password, port)

        # Step 2: Setup VPS
        setup_script = """
        apt-get update -y -qq &&
        apt-get install -y -qq curl wget git docker.io sqlite3 &&
        systemctl enable docker &&
        mkdir -p /root/.ck-nexus &&
        echo 'CK-NEXUS WORKER NODE v1.0' > /root/.ck-nexus/status.txt &&
        echo "$(date)" >> /root/.ck-nexus/status.txt &&
        echo "SETUP_COMPLETE" || echo "SETUP_FAILED"
        """

        result = self.execute_remote(ip, setup_script, port)

        if result.get("success") and "SETUP_COMPLETE" in result.get("stdout", ""):
            self._save_node(ip, port, "active")
            return {"status": "success", "ip": ip}

        return {"status": "failed", "error": result.get("stderr", "Unknown error")}

    def sync_to_node(self, ip: str, local_files: List[str], port: int = 22) -> bool:
        """Sync files to remote VPS using rsync"""
        try:
            for filepath in local_files:
                if os.path.exists(filepath):
                    cmd = (
                        f'rsync -avz -e "ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no -p {port}" '
                        f'{filepath} root@{ip}:/root/.ck-nexus/'
                    )
                    subprocess.run(cmd, shell=True, capture_output=True, timeout=60)
            return True
        except:
            return False

    def backup_to_node(self, ip: str, port: int = 22) -> bool:
        """Backup local databases to remote VPS"""
        files_to_backup = [
            "/workspace/ck-nexus/nexus_system_sd.db",
            "/workspace/ck-nexus/nexus_cache_sd.db",
            "/workspace/ck-nexus/nexus_health_sd.db"
        ]
        existing = [f for f in files_to_backup if os.path.exists(f)]
        return self.sync_to_node(ip, existing, port)

    def check_node_health(self, ip: str, port: int = 22) -> Dict[str, Any]:
        """Check remote VPS health"""
        cmd = "uptime && free -h | head -2 && df -h / | tail -1 && cat /root/.ck-nexus/status.txt 2>/dev/null"
        result = self.execute_remote(ip, cmd, port)

        if result.get("success"):
            return {
                "status": "online",
                "ip": ip,
                "info": result["stdout"][:500]
            }
        return {"status": "offline", "ip": ip}

    def _save_node(self, ip: str, port: int, status: str):
        """Save VPS node to local database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS vps_nodes (
                    ip TEXT PRIMARY KEY, port INTEGER, status TEXT,
                    last_seen TEXT, created_at TEXT DEFAULT (datetime('now'))
                )''')
                conn.execute(
                    "INSERT OR REPLACE INTO vps_nodes (ip, port, status, last_seen) VALUES (?, ?, ?, ?)",
                    (ip, port, status, time.strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
        except:
            pass

    def get_all_nodes(self) -> List[Dict]:
        """Get all managed VPS nodes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM vps_nodes ORDER BY created_at DESC").fetchall()
                return [dict(r) for r in rows]
        except:
            return []

    def get_node_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute("SELECT COUNT(*) FROM vps_nodes").fetchone()[0]
        except:
            return 0


_takeover = None

def get_vps_takeover() -> NexusVPSTakeoverPlugin:
    global _takeover
    if _takeover is None:
        _takeover = NexusVPSTakeoverPlugin()
    return _takeover


if __name__ == "__main__":
    plugin = get_vps_takeover()
    print("🔑 CK-NEXUS VPS Takeover Plugin")
    print(f"  SSH Key: {plugin.ssh_key_path}")
    print(f"  Public Key: {plugin.get_public_key()[:50]}...")
    print(f"  Nodes: {plugin.get_node_count()}")
