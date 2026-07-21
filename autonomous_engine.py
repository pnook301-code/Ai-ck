#!/usr/bin/env python3
"""
CK-NEXUS v0.8-AUTONOMOUS CONTROL
Proactive Loop Engine - AI monitors, decides, and acts
"""

import os
import time
import json
import asyncio
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, List, Any

import sys
sys.path.insert(0, os.path.dirname(__file__))
from auto_system import get_system


class NexusAutonomousEngine:
    """Autonomous Control Engine - AI monitors and acts independently"""

    def __init__(self):
        self.system = get_system()
        self.db_path = str(Path.home() / ".ck-nexus" / "nexus_memory.db")
        self.is_running = False
        self.risk_threshold = 0.7

        # Job folders
        self.watch_folder = "/workspace/ck-nexus/autonomous_jobs"
        self.success_folder = "/workspace/ck-nexus/autonomous_jobs/completed"
        self.failed_folder = "/workspace/ck-nexus/autonomous_jobs/failed"

        self._init_folders()
        self._init_db()

    def _init_folders(self):
        for folder in [self.watch_folder, self.success_folder, self.failed_folder]:
            os.makedirs(folder, exist_ok=True)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS autonomous_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                task TEXT,
                decision TEXT,
                risk_score REAL,
                details TEXT
            )''')
            conn.commit()

    def _log_autonomous(self, action: str, task: str, decision: str, risk: float, details: str = ""):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO autonomous_logs (timestamp, action, task, decision, risk_score, details) VALUES (?, ?, ?, ?, ?, ?)",
                (timestamp, action, task, decision, risk, details)
            )
            conn.commit()

    async def start_monitoring_loop(self):
        """Main autonomous loop - monitors and acts continuously"""
        self.is_running = True
        self._log_autonomous("Engine Started", "System", "ACTIVE", 0.0, "Autonomous loop online")
        print("🤖 [AUTONOMOUS ENGINE]: เริ่มทำงานอัตโนมัติแล้ว!")

        while self.is_running:
            try:
                await self._check_incoming_jobs()
                await self._perform_self_health_audit()
                await self._optimize_system_performance()
            except Exception as e:
                self._log_autonomous("Loop Error", "System", "ERROR", 0.0, str(e))

            await asyncio.sleep(5)

    async def _check_incoming_jobs(self):
        """Scan for new jobs and auto-execute if safe"""
        try:
            files = [f for f in os.listdir(self.watch_folder)
                     if f.endswith(".json") and os.path.isfile(os.path.join(self.watch_folder, f))]
        except:
            return

        for filename in files:
            file_path = os.path.join(self.watch_folder, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    job_data = json.load(f)

                task = job_data.get("task", "")
                priority = job_data.get("priority", "medium")

                decision = self._analyze_and_decide(task, priority)

                if decision["action"] == "PROCEED":
                    print(f"  ✅ [AUTO]: ลุยงาน '{task[:50]}' (risk={decision['risk_score']})")
                    self._log_autonomous("Job Started", task, "PROCEED", decision["risk_score"])

                    result = self.system.chat_sync(f"ทำงานนี้อัตโนมัติ: {task}")

                    shutil.move(file_path, os.path.join(self.success_folder, filename))
                    self._log_autonomous("Job Completed", task, "SUCCESS", decision["risk_score"],
                                         result.get("response", "")[:200])
                    print(f"  ✅ [AUTO]: เสร็จแล้ว! ย้ายไป completed/")
                else:
                    print(f"  ❌ [AUTO]: ปฏิเสธ '{task[:50]}' (risk={decision['risk_score']})")
                    self._log_autonomous("Job Rejected", task, "HOLD", decision["risk_score"])

                    shutil.move(file_path, os.path.join(self.failed_folder, filename))
                    self._log_autonomous("Job Moved", task, "MOVED_TO_FAILED", decision["risk_score"])

            except json.JSONDecodeError:
                self._log_autonomous("Parse Error", filename, "INVALID_JSON", 0.0)
            except Exception as e:
                self._log_autonomous("Job Error", filename, "ERROR", 0.0, str(e)[:100])

    def _analyze_and_decide(self, task: str, priority: str) -> Dict[str, Any]:
        """Risk assessment - decides PROCEED or HOLD"""
        task_lower = task.lower()
        risk_score = 0.2

        # High risk patterns
        high_risk = ["delete", "remove", "ลบ", "format", "shutdown", "rm -rf",
                      "drop table", "destroy", "kill", "stop", "ปิด"]
        if any(kw in task_lower for kw in high_risk):
            risk_score = 0.9

        # Medium risk patterns
        medium_risk = ["modify", "edit", "change", "แก้ไข", "เปลี่ยน", "update", "deploy"]
        if any(kw in task_lower for kw in medium_risk):
            risk_score = 0.5

        # Low risk patterns (safe to auto)
        low_risk = ["scan", "check", "read", "list", "show", "analyze", "วิเคราะห์", "สแกน", "ตรวจสอบ"]
        if any(kw in task_lower for kw in low_risk):
            risk_score = 0.1

        # Priority override
        if priority == "critical":
            risk_score = min(risk_score + 0.2, 1.0)
        elif priority == "low":
            risk_score = max(risk_score - 0.1, 0.0)

        action = "PROCEED" if risk_score < self.risk_threshold else "HOLD"
        return {"risk_score": risk_score, "action": action}

    async def _perform_self_health_audit(self):
        """Self-healing - auto-fix issues"""
        try:
            cache_stats = self.system.cache.stats()
            if cache_stats["entries"] > 10000:
                self._log_autonomous("Health Alert", "Cache", "CLEANUP_NEEDED", 0.3,
                                     f"Cache has {cache_stats['entries']} entries")
        except:
            pass

    async def _optimize_system_performance(self):
        """Auto-optimize database performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                log_count = conn.execute("SELECT COUNT(*) FROM autonomous_logs").fetchone()[0]
                if log_count > 5000:
                    conn.execute("""
                        DELETE FROM autonomous_logs WHERE id IN (
                            SELECT id FROM autonomous_logs ORDER BY id ASC LIMIT 1000
                        )
                    """)
                    conn.commit()
                    self._log_autonomous("Self-Optimize", "DB", "CLEANED", 0.0,
                                         f"Removed old logs, kept {log_count - 1000}")
        except:
            pass

    def get_logs(self, limit: int = 20) -> List[Dict]:
        """Get recent autonomous logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM autonomous_logs ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [dict(row) for row in rows]
        except:
            return []

    def get_stats(self) -> Dict:
        """Get autonomous engine statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM autonomous_logs").fetchone()[0]
                success = conn.execute(
                    "SELECT COUNT(*) FROM autonomous_logs WHERE decision='SUCCESS'"
                ).fetchone()[0]
                rejected = conn.execute(
                    "SELECT COUNT(*) FROM autonomous_logs WHERE decision='HOLD'"
                ).fetchone()[0]
                return {"total": total, "success": success, "rejected": rejected}
        except:
            return {"total": 0, "success": 0, "rejected": 0}

    def stop(self):
        self.is_running = False
        self._log_autonomous("Engine Stopped", "System", "OFFLINE", 0.0)


_engine = None

def get_autonomous_engine() -> NexusAutonomousEngine:
    global _engine
    if _engine is None:
        _engine = NexusAutonomousEngine()
    return _engine


if __name__ == "__main__":
    engine = get_autonomous_engine()
    print("🤖 Autonomous Engine Stats:", engine.get_stats())
    print("📋 Recent Logs:")
    for log in engine.get_logs(5):
        print(f"  [{log['timestamp']}] {log['action']}: {log['task'][:40]} -> {log['decision']}")
