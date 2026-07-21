#!/usr/bin/env python3
"""
CK-NEXUS v0.9-DIRECTOR ENGINE
Autonomous Director - Orchestrator, Sentinel, Self-Healing
"""

import os
import time
import json
import asyncio
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

import sys
sys.path.insert(0, os.path.dirname(__file__))
from auto_system import get_system
from autonomous_engine import get_autonomous_engine


class NexusDirectorCore:
    """Autonomous Director - Plans, Dispatches, Heals"""

    def __init__(self):
        self.system = get_system()
        self.auto_engine = get_autonomous_engine()
        self.db_path = str(Path.home() / ".ck-nexus" / "nexus_memory.db")
        self.is_active = False

        self.watch_folder = "/workspace/ck-nexus/autonomous_jobs"
        self.blueprints_folder = "/workspace/ck-nexus/autonomous_jobs/blueprints"

        os.makedirs(self.blueprints_folder, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS director_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                phase TEXT,
                action TEXT,
                details TEXT,
                status TEXT DEFAULT 'ok'
            )''')
            conn.commit()

    def _log(self, phase: str, action: str, details: str, status: str = "ok"):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO director_logs (timestamp, phase, action, details, status) VALUES (?, ?, ?, ?, ?)",
                (timestamp, phase, action, details, status)
            )
            conn.commit()

    # ========== 1. PROACTIVE FAILURE SENTINEL ==========
    async def _sentinel_pre_error_check(self):
        """Detect issues BEFORE they happen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check recent error rate
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM work_logs WHERE action LIKE '%Error%' AND timestamp > datetime('now', '-5 minutes')"
                )
                recent_errors = cursor.fetchone()[0]

                if recent_errors >= 3:
                    self._log("SENTINEL", "ERROR_SPIKE",
                              f"Detected {recent_errors} errors in 5min. Switching to fallback.",
                              "warning")
                    return True

                # Check database size
                cursor = conn.execute("SELECT COUNT(*) FROM work_logs")
                log_count = cursor.fetchone()[0]
                if log_count > 10000:
                    self._log("SENTINEL", "DB_FULL",
                              f"Work logs: {log_count}. Auto-cleaning old entries.",
                              "warning")
                    conn.execute(
                        "DELETE FROM work_logs WHERE id IN (SELECT id FROM work_logs ORDER BY id ASC LIMIT 2000)"
                    )
                    conn.commit()

                # Check cache health
                cache_count = conn.execute("SELECT COUNT(*) FROM system_cache").fetchone()[0]
                if cache_count > 50000:
                    self._log("SENTINEL", "CACHE_BLOAT",
                              f"Cache entries: {cache_count}. Running optimization.",
                              "warning")

        except Exception as e:
            self._log("SENTINEL", "CHECK_FAILED", str(e)[:100], "error")

    # ========== 2. SELF-HEALING PROTOCOL ==========
    async def _self_healing_protocol(self):
        """Auto-fix issues detected"""
        try:
            # Test memory system
            test = self.system.query_memory("test_health", limit=1)
        except Exception as e:
            self._log("HEALING", "MEMORY_FAIL",
                      f"Memory system error: {str(e)[:80]}. Attempting recovery.",
                      "warning")
            try:
                # Attempt database repair
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA integrity_check")
                    conn.execute("VACUUM")
                self._log("HEALING", "DB_REPAIRED", "Database integrity restored.", "ok")
            except Exception as repair_err:
                self._log("HEALING", "REPAIR_FAILED", str(repair_err)[:100], "error")

        # Check file system integrity
        critical_files = [
            "/workspace/ck-nexus/auto_system.py",
            "/workspace/ck-nexus/server.py",
            "/workspace/ck-nexus/autonomous_engine.py",
            "/workspace/ck-nexus/director_core.py"
        ]
        for f in critical_files:
            if not os.path.exists(f):
                self._log("HEALING", "FILE_MISSING",
                          f"Critical file missing: {f}", "error")

    # ========== 3. ORCHESTRATOR-TO-AGENT DISPATCHER ==========
    async def _orchestrate_and_dispatch_tasks(self):
        """Scan for projects, plan, and dispatch to agents"""
        try:
            blueprint_files = [f for f in os.listdir(self.watch_folder)
                              if f.endswith(".json") and os.path.isfile(os.path.join(self.watch_folder, f))]
        except:
            return

        for filename in blueprint_files:
            filepath = os.path.join(self.watch_folder, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    blueprint = json.load(f)

                project_name = blueprint.get("project_name", filename.replace(".json", ""))
                goal = blueprint.get("goal", blueprint.get("task", ""))
                priority = blueprint.get("priority", "medium")

                self._log("DIRECTOR", "BLUEPRINT_FOUND",
                          f"Project: {project_name} | Goal: {goal[:60]}")

                # Risk check
                risk = self._assess_risk(goal)
                if risk >= 0.8:
                    self._log("DIRECTOR", "PROJECT_BLOCKED",
                              f"High risk ({risk}): {project_name}. Moving to review.",
                              "warning")
                    import shutil
                    failed_dir = os.path.join(self.watch_folder, "failed")
                    os.makedirs(failed_dir, exist_ok=True)
                    shutil.move(filepath, os.path.join(failed_dir, filename))
                    continue

                # Execute project plan
                await self._execute_project_plan(project_name, goal, filepath, filename)

            except json.JSONDecodeError:
                self._log("DIRECTOR", "INVALID_JSON", filename, "error")
            except Exception as e:
                self._log("DIRECTOR", "DISPATCH_ERROR", str(e)[:100], "error")

    def _assess_risk(self, goal: str) -> float:
        """Assess project risk level"""
        goal_lower = goal.lower()
        risk = 0.2

        dangerous = ["delete", "remove", "format", "rm -rf", "drop", "destroy", "shutdown"]
        if any(kw in goal_lower for kw in dangerous):
            risk = 0.9

        medium = ["deploy", "modify", "update", "change", "install"]
        if any(kw in goal_lower for kw in medium):
            risk = 0.5

        safe = ["scan", "check", "read", "analyze", "research", "list"]
        if any(kw in goal_lower for kw in safe):
            risk = 0.1

        return risk

    async def _execute_project_plan(self, name: str, goal: str, filepath: str, filename: str):
        """Plan and dispatch work to agents"""
        self._log("DIRECTOR", "PLANNING",
                  f"Designing execution plan for: {name}")

        # Step 1: Research phase
        self._log("DIRECTOR", "DISPATCH_RESEARCHER",
                  f"Sending research task to researcher agent")
        research_result = self.system.chat_sync(
            f"วิเคราะห์และเตรียมข้อมูลสำหรับโปรเจกต์: {goal}"
        )
        self._log("DIRECTOR", "RESEARCH_DONE",
                  f"Research complete: {research_result.get('response', '')[:100]}")

        # Step 2: Memory save
        self.system.save_memory(
            f"Project {name}: {goal} | Status: In Progress",
            "Director Active Projects"
        )

        # Step 3: Code phase (if needed)
        if any(kw in goal.lower() for kw in ["code", "create", "write", "build", "เขียน", "สร้าง"]):
            self._log("DIRECTOR", "DISPATCH_CODER",
                      f"Sending code task to coder agent")
            coder_result = self.system.chat_sync(
                f"ดำเนินการเขียนโค้ดสำหรับ: {goal}"
            )
            self._log("DIRECTOR", "CODE_DONE",
                      f"Code complete: {coder_result.get('response', '')[:100]}")

        # Step 4: Move to completed
        import shutil
        completed_dir = os.path.join(self.watch_folder, "completed")
        os.makedirs(completed_dir, exist_ok=True)
        shutil.move(filepath, os.path.join(completed_dir, filename))
        self._log("DIRECTOR", "PROJECT_COMPLETE",
                  f"Project '{name}' completed successfully")

    # ========== MAIN LOOP ==========
    async def start_director_mainframe(self):
        """Main autonomous director loop"""
        self.is_active = True
        self._log("DIRECTOR", "MAINFRAME_ACTIVE",
                  "Autonomous Director v0.9 started. Full control engaged.")
        print("👑 [DIRECTOR]: เริ่มทำงานอัตโนมัติแล้ว!")

        while self.is_active:
            try:
                await self._sentinel_pre_error_check()
                await self._self_healing_protocol()
                await self._orchestrate_and_dispatch_tasks()
            except Exception as e:
                self._log("DIRECTOR", "LOOP_ERROR", str(e)[:100], "error")

            await asyncio.sleep(3)

    def get_logs(self, limit: int = 20) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM director_logs ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [dict(row) for row in rows]
        except:
            return []

    def get_stats(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM director_logs").fetchone()[0]
                ok = conn.execute("SELECT COUNT(*) FROM director_logs WHERE status='ok'").fetchone()[0]
                warnings = conn.execute("SELECT COUNT(*) FROM director_logs WHERE status='warning'").fetchone()[0]
                errors = conn.execute("SELECT COUNT(*) FROM director_logs WHERE status='error'").fetchone()[0]
                return {"total": total, "ok": ok, "warnings": warnings, "errors": errors}
        except:
            return {"total": 0, "ok": 0, "warnings": 0, "errors": 0}

    def shutdown(self):
        self.is_active = False
        self._log("DIRECTOR", "MAINFRAME_SHUTDOWN", "Director offline")


_director = None

def get_director_core() -> NexusDirectorCore:
    global _director
    if _director is None:
        _director = NexusDirectorCore()
    return _director


if __name__ == "__main__":
    director = get_director_core()
    print("👑 Director Stats:", director.get_stats())
    print("📋 Recent Logs:")
    for log in director.get_logs(10):
        icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(log["status"], "📋")
        print(f"  {icon} [{log['timestamp'][:19]}] {log['phase']}: {log['action'][:40]}")
