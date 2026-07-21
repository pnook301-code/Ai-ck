#!/usr/bin/env python3
"""
CK-NEXUS v1.0 - Cognitive Planning Engine
Think Before You Act - Proactive Planning System
"""

import os
import time
import json
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional


class NexusCognitivePlanner:
    """AI Cognitive Planning Engine - Think before act"""

    def __init__(self, base_path: str = "/workspace/ck-nexus"):
        self.base_path = base_path
        self.db_path = os.path.join(base_path, "nexus_system_sd.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS execution_blueprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task_name TEXT,
                task_category TEXT,
                required_tools TEXT,
                assigned_vps_node TEXT,
                risk_assessment TEXT,
                risk_score REAL,
                steps_json TEXT,
                fallback_plan TEXT,
                status TEXT DEFAULT 'PLANNED',
                execution_time_ms REAL,
                completed_at TEXT
            )''')
            conn.commit()

    def create_blueprint(self, task: str) -> Dict[str, Any]:
        """Create execution blueprint - Think before act"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        task_lower = task.lower()

        # Step 1: Check system resources
        storage = self._check_storage()

        # Step 2: Analyze task and select tools
        category, tools, node, risk_score, steps, fallback = self._analyze_task(task, task_lower, storage)

        # Step 3: Auto-critical if storage low
        if storage["free_pct"] < 15.0:
            risk_score = min(risk_score + 0.3, 1.0)
            steps.insert(0, "🚨 CRITICAL: Storage low - run cleanup first")

        risk_level = self._score_to_level(risk_score)

        blueprint = {
            "timestamp": timestamp,
            "task_name": task,
            "task_category": category,
            "required_tools": ", ".join(tools),
            "assigned_vps_node": node,
            "risk_assessment": risk_level,
            "risk_score": risk_score,
            "steps_json": json.dumps(steps, ensure_ascii=False),
            "fallback_plan": fallback,
            "status": "PLANNED"
        }

        # Save to database
        self._save_blueprint(blueprint)

        return blueprint

    def _check_storage(self) -> Dict:
        try:
            total, used, free = shutil.disk_usage(self.base_path)
            return {
                "total_gb": round(total / (2**30), 2),
                "free_gb": round(free / (2**30), 2),
                "free_pct": round((free / total) * 100, 2)
            }
        except:
            return {"total_gb": 0, "free_gb": 0, "free_pct": 100}

    def _analyze_task(self, task: str, task_lower: str, storage: Dict):
        """Analyze task and determine tools, node, risk, steps"""

        # VPS/Server tasks
        if any(kw in task_lower for kw in ["vps", "server", "บอท", "ขุด", "deploy", "docker"]):
            return (
                "VPS_OPERATION",
                ["SSH_Control", "Docker", "Network_Scanner"],
                "Oracle Cloud (ARM 4OCPU/24GB)",
                0.4,
                [
                    "1. Check SSH key access to target VPS",
                    "2. Connect and verify system status",
                    "3. Deploy Docker container sandbox",
                    "4. Execute task in isolated environment",
                    "5. Monitor and log results"
                ],
                "Switch to backup VPS node if primary fails"
            )

        # Registration tasks
        if any(kw in task_lower for kw in ["สมัคร", "ลงทะเบียน", "register", "sign up", "เว็บ"]):
            return (
                "WEB_REGISTRATION",
                ["Playwright_Headless", "ADB_Phone_Bridge", "Email_Verifier"],
                "Local WebAgent Core",
                0.5,
                [
                    "1. Analyze target website form structure",
                    "2. Fill registration form with profile data",
                    "3. Monitor for OTP requirement via ADB",
                    "4. Wait for verification email",
                    "5. Auto-click verification link",
                    "6. Save registration status to DB"
                ],
                "Manual registration required if CAPTCHA detected"
            )

        # Knowledge mining tasks
        if any(kw in task_lower for kw in ["ขุด", "mining", "knowledge", "搜集", "research", "สแกน"]):
            return (
                "KNOWLEDGE_MINING",
                ["Web_Scraper", "Vector_Embedding", "SQLite_Cache"],
                "Distributed Hive Nodes",
                0.3,
                [
                    "1. Define search topics and keywords",
                    "2. Distribute scraping tasks across VPS nodes",
                    "3. Collect and preprocess data",
                    "4. Generate embeddings for vector store",
                    "5. Store knowledge in local SQLite cache"
                ],
                "Fallback to local Groq API for analysis"
            )

        # Backup tasks
        if any(kw in task_lower for kw in ["backup", "สำรอง", "sync", "mirror"]):
            return (
                "BACKUP_OPERATION",
                ["SQLite_Backup", "RSync", "Cloud_Mirror"],
                "Google Cloud Mirror",
                0.2,
                [
                    "1. Create local database backup (zip)",
                    "2. Verify backup integrity",
                    "3. Sync to primary mirror node",
                    "4. Sync to secondary mirror node",
                    "5. Verify cross-region replication"
                ],
                "Keep local backup if cloud sync fails"
            )

        # Security tasks
        if any(kw in task_lower for kw in ["security", "ปลอดภัย", "scan", "audit", "สแกน"]):
            return (
                "SECURITY_AUDIT",
                ["Vulnerability_Scanner", "Port_Scanner", "Log_Analyzer"],
                "Local + VPS Scanner",
                0.3,
                [
                    "1. Scan system for known vulnerabilities",
                    "2. Check open ports and services",
                    "3. Analyze log files for anomalies",
                    "4. Generate security report",
                    "5. Apply patches if safe to do so"
                ],
                "Quarantine affected systems if critical"
            )

        # Default: General task
        return (
            "GENERAL_TASK",
            ["SQLite_Cache_Layer", "Groq_Mainframe"],
            "Local Processing",
            0.1,
            [
                "1. Check cache for similar queries",
                "2. If not cached, query Groq API",
                "3. Process and validate response",
                "4. Cache result for future use"
            ],
            "Retry with different model if API fails"
        )

    def _score_to_level(self, score: float) -> str:
        if score < 0.3:
            return "LOW"
        elif score < 0.6:
            return "MEDIUM"
        elif score < 0.8:
            return "HIGH"
        else:
            return "CRITICAL"

    def _save_blueprint(self, blueprint: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO execution_blueprints 
                    (timestamp, task_name, task_category, required_tools, assigned_vps_node, 
                     risk_assessment, risk_score, steps_json, fallback_plan, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    blueprint["timestamp"], blueprint["task_name"],
                    blueprint["task_category"], blueprint["required_tools"],
                    blueprint["assigned_vps_node"], blueprint["risk_assessment"],
                    blueprint["risk_score"], blueprint["steps_json"],
                    blueprint["fallback_plan"], blueprint["status"]
                ))
                conn.commit()
        except:
            pass

    def execute_blueprint(self, blueprint: Dict) -> Dict[str, Any]:
        """Execute a planned blueprint"""
        timestamp = blueprint["timestamp"]
        steps = json.loads(blueprint["steps_json"])

        start_time = time.perf_counter()

        for i, step in enumerate(steps):
            # Log each step
            self._log_execution(blueprint["task_name"], f"Step {i+1}: {step}")

        # Update status
        execution_time = (time.perf_counter() - start_time) * 1000

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE execution_blueprints SET status = 'EXECUTED', execution_time_ms = ?, completed_at = ? WHERE timestamp = ?",
                    (execution_time, time.strftime("%Y-%m-%d %H:%M:%S"), timestamp)
                )
                conn.commit()
        except:
            pass

        return {
            "status": "EXECUTED",
            "task": blueprint["task_name"],
            "steps_completed": len(steps),
            "execution_time_ms": round(execution_time)
        }

    def _log_execution(self, task: str, action: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO work_logs (timestamp, action, details) VALUES (?, ?, ?)",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), f"Cognitive: {task}", action)
                )
                conn.commit()
        except:
            pass

    def get_recent_blueprints(self, limit: int = 10) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM execution_blueprints ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [dict(r) for r in rows]
        except:
            return []

    def get_stats(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM execution_blueprints").fetchone()[0]
                executed = conn.execute("SELECT COUNT(*) FROM execution_blueprints WHERE status='EXECUTED'").fetchone()[0]
                planned = conn.execute("SELECT COUNT(*) FROM execution_blueprints WHERE status='PLANNED'").fetchone()[0]
                return {"total": total, "executed": executed, "planned": planned}
        except:
            return {"total": 0, "executed": 0, "planned": 0}

    def generate_report(self) -> str:
        stats = self.get_stats()
        recent = self.get_recent_blueprints(5)

        report = []
        report.append("=" * 60)
        report.append("🧠 COGNITIVE PLANNER STATUS")
        report.append("=" * 60)
        report.append(f"  Total Blueprints: {stats['total']}")
        report.append(f"  Executed: {stats['executed']}")
        report.append(f"  Planned: {stats['planned']}")
        report.append("")

        if recent:
            report.append("  📋 Recent Blueprints:")
            for bp in recent:
                icon = "✅" if bp["status"] == "EXECUTED" else "📋"
                report.append(f"    {icon} [{bp['timestamp'][:16]}] {bp['task_name'][:40]}")
                report.append(f"       Tools: {bp['required_tools'][:40]}")
                report.append(f"       Risk: {bp['risk_assessment']}")

        report.append("=" * 60)
        return "\n".join(report)


_planner = None

def get_cognitive_planner() -> NexusCognitivePlanner:
    global _planner
    if _planner is None:
        _planner = NexusCognitivePlanner()
    return _planner


if __name__ == "__main__":
    planner = get_cognitive_planner()

    print("🧠 CK-NEXUS Cognitive Planner - TEST")
    print("=" * 60)

    # Test 1: Create blueprint for VPS task
    print("\n📋 TEST 1: VPS Deployment Blueprint")
    bp = planner.create_blueprint("deploy docker bot on vps for data mining")
    print(f"  Category: {bp['task_category']}")
    print(f"  Tools: {bp['required_tools']}")
    print(f"  Node: {bp['assigned_vps_node']}")
    print(f"  Risk: {bp['risk_assessment']} ({bp['risk_score']})")
    print(f"  Steps: {len(json.loads(bp['steps_json']))}")

    # Test 2: Create blueprint for registration
    print("\n📋 TEST 2: Web Registration Blueprint")
    bp2 = planner.create_blueprint("ลงทะเบียนสมัครสมาชิกเว็บ forum ใหม่")
    print(f"  Category: {bp2['task_category']}")
    print(f"  Risk: {bp2['risk_assessment']} ({bp2['risk_score']})")

    # Test 3: Execute blueprint
    print("\n📋 TEST 3: Execute Blueprint")
    result = planner.execute_blueprint(bp)
    print(f"  Status: {result['status']}")
    print(f"  Steps: {result['steps_completed']}")
    print(f"  Time: {result['execution_time_ms']}ms")

    # Test 4: Stats
    print("\n📊 TEST 4: Stats")
    print(f"  {planner.get_stats()}")

    # Test 5: Report
    print(planner.generate_report())
