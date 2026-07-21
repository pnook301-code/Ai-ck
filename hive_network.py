#!/usr/bin/env python3
"""
CK-NEXUS v1.0 - Hive Network Manager
Distributed VPS cluster management
"""

import os
import time
import json
import sqlite3
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Any


class HiveNetworkManager:
    """Manage distributed VPS cluster"""

    def __init__(self, base_path: str = "/workspace/ck-nexus"):
        self.base_path = base_path
        self.db_path = os.path.join(base_path, "nexus_system_sd.db")
        self.nodes_path = os.path.join(base_path, "hive_nodes.json")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS hive_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_name TEXT UNIQUE,
                ip_address TEXT,
                port INTEGER DEFAULT 22,
                role TEXT DEFAULT 'worker',
                status TEXT DEFAULT 'pending',
                last_heartbeat TEXT,
                capabilities TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS distributed_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT,
                assigned_node TEXT,
                task_data TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT
            )''')
            conn.commit()

    def register_node(self, name: str, ip: str, port: int = 22, role: str = "worker") -> bool:
        """Register a VPS node in the hive"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO hive_nodes (node_name, ip_address, port, role, status) VALUES (?, ?, ?, ?, ?)",
                    (name, ip, port, role, "active")
                )
                conn.commit()
            return True
        except:
            return False

    def get_active_nodes(self) -> List[Dict]:
        """Get all active nodes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM hive_nodes WHERE status = 'active'"
                ).fetchall()
                return [dict(r) for r in rows]
        except:
            return []

    def get_node_count(self) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute(
                    "SELECT COUNT(*) FROM hive_nodes WHERE status = 'active'"
                ).fetchone()[0]
        except:
            return 0

    def distribute_task(self, task_type: str, task_data: str) -> Dict[str, Any]:
        """Distribute a task to available nodes"""
        nodes = self.get_active_nodes()
        if not nodes:
            return {"status": "no_nodes", "error": "No active nodes available"}

        # Simple round-robin distribution
        task_id = f"task_{int(time.time())}"
        assigned = nodes[0]  # Assign to first available node

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO distributed_tasks (id, task_type, assigned_node, task_data) VALUES (?, ?, ?, ?)",
                    (task_id, task_type, assigned["node_name"], task_data)
                )
                conn.commit()
        except:
            pass

        return {
            "status": "distributed",
            "task_id": task_id,
            "assigned_to": assigned["node_name"],
            "node_ip": assigned["ip_address"]
        }

    def run_knowledge_mining(self, topics: List[str]) -> Dict[str, Any]:
        """Distribute knowledge mining tasks across nodes"""
        nodes = self.get_active_nodes()
        if not nodes:
            return {"status": "no_nodes"}

        results = {}
        for i, topic in enumerate(topics):
            node = nodes[i % len(nodes)]
            task_data = json.dumps({"topic": topic, "action": "mine_knowledge"})
            self.distribute_task("knowledge_mining", task_data)
            results[topic] = node["node_name"]

        return {"status": "distributed", "tasks": results}

    def sync_backup_to_all(self) -> Dict[str, Any]:
        """Sync backup to all active nodes"""
        from vps_takeover_plugin import get_vps_takeover
        takeover = get_vps_takeover()

        nodes = self.get_active_nodes()
        results = {}
        for node in nodes:
            success = takeover.backup_to_node(node["ip_address"], node["port"])
            results[node["node_name"]] = "synced" if success else "failed"

        return results

    def check_all_nodes_health(self) -> Dict[str, Any]:
        """Check health of all nodes"""
        from vps_takeover_plugin import get_vps_takeover
        takeover = get_vps_takeover()

        nodes = self.get_active_nodes()
        results = {}
        for node in nodes:
            health = takeover.check_node_health(node["ip_address"], node["port"])
            results[node["node_name"]] = health["status"]

            # Update last heartbeat
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "UPDATE hive_nodes SET last_heartbeat = ? WHERE node_name = ?",
                        (time.strftime("%Y-%m-%d %H:%M:%S"), node["node_name"])
                    )
                    conn.commit()
            except:
                pass

        return results

    def generate_report(self) -> str:
        """Generate cluster status report"""
        nodes = self.get_active_nodes()
        report = []
        report.append("=" * 60)
        report.append("🐝 CK-NEXUS HIVE NETWORK STATUS")
        report.append("=" * 60)
        report.append(f"  Active Nodes: {len(nodes)}")
        report.append("")

        for node in nodes:
            report.append(f"  🟢 {node['node_name']}")
            report.append(f"     IP: {node['ip_address']}")
            report.append(f"     Role: {node['role']}")
            report.append(f"     Last Seen: {node['last_heartbeat'] or 'Never'}")

        report.append("=" * 60)
        return "\n".join(report)


_hive = None

def get_hive_manager() -> HiveNetworkManager:
    global _hive
    if _hive is None:
        _hive = HiveNetworkManager()
    return _hive


if __name__ == "__main__":
    manager = get_hive_manager()
    print(manager.generate_report())
