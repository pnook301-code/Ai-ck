#!/usr/bin/env python3
"""
CK-NEXUS v0.95-PROTOCOLS
Protocol 1: Auto-Backup
Protocol 2: Telegram/Line Notifier
Protocol 3: Email Task Ingestion
"""

import os
import sys
import json
import time
import sqlite3
import shutil
import hashlib
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))


class TelegramNotifier:
    """Send status updates to Telegram"""

    def __init__(self):
        self.config_path = os.path.expanduser("~/.codex/telegram-bridge.json")
        self.config = self._load_config()
        self.sender_script = "/root/.opencode/skills/shared_skills/telegram-bridge-send/scripts/send_telegram.py"

    def _load_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def is_configured(self) -> bool:
        return bool(self.config.get("botToken"))

    def send(self, message: str) -> bool:
        if not self.is_configured():
            print("⚠️ Telegram not configured. Add botToken to ~/.codex/telegram-bridge.json")
            return False

        try:
            result = subprocess.run(
                ["python3", self.sender_script, "--message", message],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"⚠️ Telegram send error: {e}")
            return False

    def send_health_report(self, report: Dict) -> bool:
        msg = (
            f"⚡ CK-NEXUS v0.95 Health Report\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Latency: {report.get('latency', 'N/A')}\n"
            f"📦 Cache: {report.get('cache', 'N/A')}\n"
            f"💾 Storage: {report.get('storage', 'N/A')}\n"
            f"🛡️ Integrity: {report.get('integrity', 'N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {report.get('timestamp', 'N/A')}"
        )
        return self.send(msg)

    def send_alert(self, alert_type: str, message: str) -> bool:
        icons = {"warning": "⚠️", "error": "❌", "success": "✅", "info": "ℹ️"}
        icon = icons.get(alert_type, "📋")
        msg = f"{icon} CK-NEXUS ALERT\n━━━━━━━━━━━━━━━━━\n{message}\n━━━━━━━━━━━━━━━━━\n⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send(msg)


class AutoBackup:
    """Auto-backup system to GitHub/zip"""

    def __init__(self, base_path: str = "/workspace/ck-nexus"):
        self.base_path = base_path
        self.backup_dir = os.path.join(base_path, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self) -> Optional[str]:
        """Create zip backup of all databases"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"ck_nexus_backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_name)

        files_to_backup = [
            "nexus_system_sd.db",
            "nexus_cache_sd.db",
            "nexus_health_sd.db",
        ]

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for db_file in files_to_backup:
                    db_path = os.path.join(self.base_path, db_file)
                    if os.path.exists(db_path):
                        zf.write(db_path, db_file)

                # Also backup config
                config_path = os.path.expanduser("~/.ck-nexus/config.json")
                if os.path.exists(config_path):
                    zf.write(config_path, "config.json")

            size_kb = os.path.getsize(backup_path) / 1024
            print(f"✅ Backup created: {backup_name} ({size_kb:.1f} KB)")
            return backup_path
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None

    def cleanup_old_backups(self, keep_last: int = 5):
        """Keep only last N backups"""
        backups = sorted(Path(self.backup_dir).glob("ck_nexus_backup_*.zip"))
        if len(backups) > keep_last:
            for old in backups[:-keep_last]:
                old.unlink()
                print(f"  🗑️ Removed old backup: {old.name}")


class EmailTaskIngestion:
    """Monitor email for task files (stub - needs actual email API)"""

    def __init__(self, watch_folder: str = "/workspace/ck-nexus/autonomous_jobs"):
        self.watch_folder = watch_folder
        self.email_folder = os.path.join(watch_folder, "email_tasks")
        os.makedirs(self.email_folder, exist_ok=True)

    def check_for_email_tasks(self) -> List[Dict]:
        """Check for tasks from email (currently scans local folder)"""
        tasks = []
        try:
            for f in os.listdir(self.email_folder):
                if f.endswith(".json"):
                    filepath = os.path.join(self.email_folder, f)
                    with open(filepath) as fp:
                        task = json.load(fp)
                        task["_file"] = f
                        tasks.append(task)
        except:
            pass
        return tasks

    def create_task_from_email(self, subject: str, body: str, attachments: List[str] = None) -> str:
        """Create a task file from email content"""
        task = {
            "task": body,
            "project_name": subject,
            "priority": "medium",
            "source": "email",
            "attachments": attachments or []
        }
        filename = f"email_task_{int(time.time())}.json"
        filepath = os.path.join(self.email_folder, filename)
        with open(filepath, "w") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        return filename


class ProtocolManager:
    """Manages all 3 protocols"""

    def __init__(self):
        self.notifier = TelegramNotifier()
        self.backup = AutoBackup()
        self.email = EmailTaskIngestion()

    def run_health_check_and_notify(self) -> bool:
        """Run health check and send to Telegram"""
        from auto_system import get_system
        system = get_system()
        report = system.get_health_report()

        if self.notifier.is_configured():
            return self.notifier.send_health_report(report)
        else:
            print("📊 Health Report (Telegram not configured):")
            for k, v in report.items():
                print(f"  {k}: {v}")
            return True

    def run_backup(self) -> bool:
        """Run backup and notify"""
        path = self.backup.create_backup()
        if path:
            self.backup.cleanup_old_backups(keep_last=5)
            if self.notifier.is_configured():
                self.notifier.send_alert("success", f"Backup complete: {os.path.basename(path)}")
            return True
        return False

    def run_full_protocol(self):
        """Run all protocols"""
        print("🚀 Running all protocols...")

        # 1. Health check
        print("\n📊 Protocol 2: Health Report")
        self.run_health_check_and_notify()

        # 2. Backup
        print("\n💾 Protocol 1: Auto Backup")
        self.run_backup()

        # 3. Check email tasks
        print("\n📧 Protocol 3: Email Tasks")
        tasks = self.email.check_for_email_tasks()
        if tasks:
            print(f"  Found {len(tasks)} email tasks")
            for t in tasks:
                print(f"  - {t.get('project_name', 'Unknown')}: {t.get('task', '')[:50]}")
        else:
            print("  No email tasks pending")


_protocol = None

def get_protocol_manager() -> ProtocolManager:
    global _protocol
    if _protocol is None:
        _protocol = ProtocolManager()
    return _protocol


if __name__ == "__main__":
    pm = get_protocol_manager()
    pm.run_full_protocol()
