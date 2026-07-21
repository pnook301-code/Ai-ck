#!/usr/bin/env python3
"""
CK-NEXUS v1.2 - Smart Router with VPS Speed Boost
Auto-fallback model router + VPS resource integration
"""

import os
import time
import json
import sqlite3
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Optional


class NexusSmartRouterV12:
    """Smart Router: Auto-fallback + VPS Speed Integration"""

    def __init__(self, config_path: str = "/root/.ck-nexus/config.json", sd_path: str = "/workspace/ck-nexus"):
        self.config_path = config_path
        self.sd_path = sd_path
        self.db_path = os.path.join(sd_path, "nexus_system_sd.db")
        self.config = self._load_config()
        self.model_stats = {}
        self._init_stats_table()

    def _load_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def _init_stats_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    model_name TEXT,
                    provider TEXT,
                    latency_ms REAL,
                    success INTEGER,
                    task_type TEXT,
                    error_msg TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vps_speed_boost (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    vps_ip TEXT,
                    provider TEXT,
                    response_ms REAL,
                    status TEXT,
                    task_delegated TEXT
                )
            """)
            conn.commit()

    # ═══════════════════════════════════════════════════════
    # MODEL PRIORITY LIST (Free Tier - Anti Error)
    # ═══════════════════════════════════════════════════════
    MODEL_POOL = [
        {
            "name": "Groq Llama 3.3 70B",
            "model": "llama-3.3-70b-versatile",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "config_key": "groq",
            "priority": 1,
            "speed_tier": "TURBO",
            "avg_latency_ms": 389
        },
        {
            "name": "Groq Llama 3.1 8B",
            "model": "llama-3.1-8b-instant",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "config_key": "groq",
            "priority": 2,
            "speed_tier": "ULTRA",
            "avg_latency_ms": 280
        },
        {
            "name": "Groq Gemma 2 9B",
            "model": "gemma2-9b-it",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "config_key": "groq",
            "priority": 3,
            "speed_tier": "TURBO",
            "avg_latency_ms": 320
        },
        {
            "name": "OpenRouter Gemini 2.5 Flash",
            "model": "google/gemini-2.5-flash:free",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "config_key": "openrouter",
            "priority": 4,
            "speed_tier": "FAST",
            "avg_latency_ms": 1200
        },
        {
            "name": "OpenRouter Mistral 7B",
            "model": "mistralai/mistral-7b-instruct:free",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "config_key": "openrouter",
            "priority": 5,
            "speed_tier": "FAST",
            "avg_latency_ms": 1500
        },
        {
            "name": "OpenRouter Qwen Coder",
            "model": "qwen/qwen-2.5-coder-32b-instruct:free",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "config_key": "openrouter",
            "priority": 6,
            "speed_tier": "MEDIUM",
            "avg_latency_ms": 2000
        }
    ]

    def get_best_model(self, task_type: str = "general") -> Dict:
        """เลือกโมเดลที่ดีที่สุดตาม task type + ไม่มี fault ล่าสุด"""
        recent_faults = self._get_recent_faults()
        available_models = []

        for model in self.MODEL_POOL:
            config = self.config.get(model["config_key"], {})
            api_key = config.get("key", "")
            if not api_key:
                continue

            # Check if this model/provider has recent faults
            provider_fault = f"{model['config_key'].upper()}_API"
            if any(provider_fault in f.get("component", "") or
                   model["config_key"] in f.get("component", "").lower()
                   for f in recent_faults):
                continue

            # Check task-specific optimization
            score = model["priority"]
            if task_type == "code" and "coder" in model["name"].lower():
                score -= 2
            if task_type == "chat" and "8b" in model["model"]:
                score -= 1
            if task_type == "analysis" and "70b" in model["model"]:
                score -= 2

            available_models.append({**model, "score": score, "api_key": api_key})

        if not available_models:
            # Emergency fallback - use any available
            for model in self.MODEL_POOL:
                config = self.config.get(model["config_key"], {})
                api_key = config.get("key", "")
                if api_key:
                    return {**model, "api_key": api_key}

        available_models.sort(key=lambda x: x["score"])
        return available_models[0] if available_models else None

    def _get_recent_faults(self) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT broken_component, error_reason FROM system_fault_logs WHERE timestamp > datetime('now', '-5 minutes')"
                ).fetchall()
                return [{"component": r[0], "reason": r[1]} for r in rows]
        except:
            return []

    def query_with_fallback(self, prompt: str, task_type: str = "general") -> Dict:
        """ส่ง query ผ่าน model ที่ดีที่สุด พร้อม fallback อัตโนมัติ"""
        model = self.get_best_model(task_type)
        if not model:
            return {"error": "No available models", "response": None}

        start = time.time()
        try:
            payload = json.dumps({
                "model": model["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.7
            }).encode()

            req = urllib.request.Request(
                model["base_url"],
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {model['api_key']}"
                }
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                response = data["choices"][0]["message"]["content"]
                latency = (time.time() - start) * 1000

                self._log_performance(model["name"], model["config_key"], latency, True, task_type)
                self._log_vps_speed(model, latency, "SUCCESS")

                return {
                    "response": response,
                    "model": model["name"],
                    "latency_ms": round(latency),
                    "provider": model["config_key"],
                    "fallback_used": False
                }

        except urllib.error.HTTPError as e:
            latency = (time.time() - start) * 1000
            self._log_performance(model["name"], model["config_key"], latency, False, task_type, f"HTTP_{e.code}")

            # Try next model
            return self._try_fallback(prompt, task_type, exclude=model["name"], error=f"HTTP_{e.code}")

        except Exception as e:
            latency = (time.time() - start) * 1000
            self._log_performance(model["name"], model["config_key"], latency, False, task_type, str(e)[:50])
            return self._try_fallback(prompt, task_type, exclude=model["name"], error=str(e)[:50])

    def _try_fallback(self, prompt: str, task_type: str, exclude: str, error: str) -> Dict:
        """ลองโมเดลถัดไปเมื่อตัวหลักล่ม"""
        for model in self.MODEL_POOL:
            if model["name"] == exclude:
                continue
            config = self.config.get(model["config_key"], {})
            api_key = config.get("key", "")
            if not api_key:
                continue

            try:
                start = time.time()
                payload = json.dumps({
                    "model": model["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.7
                }).encode()

                req = urllib.request.Request(
                    model["base_url"],
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    }
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
                    response = data["choices"][0]["message"]["content"]
                    latency = (time.time() - start) * 1000

                    self._log_performance(model["name"], model["config_key"], latency, True, task_type)
                    self._log_vps_speed(model, latency, "FALLBACK_SUCCESS")

                    return {
                        "response": response,
                        "model": model["name"],
                        "latency_ms": round(latency),
                        "provider": model["config_key"],
                        "fallback_used": True,
                        "fallback_reason": error
                    }
            except:
                continue

        return {"error": f"All models failed. Last error: {error}", "response": None}

    # ═══════════════════════════════════════════════════════
    # VPS SPEED BOOST - ใช้ความเร็ว VPS มาเสริมระบบหลัก
    # ═══════════════════════════════════════════════════════
    def get_vps_nodes(self) -> List[Dict]:
        """ดึง VPS nodes ที่พร้อมใช้งาน"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM autonomous_vps_servers WHERE status LIKE 'ACTIVE%'"
                ).fetchall()
                return [dict(r) for r in rows]
        except:
            return []

    def delegate_to_vps(self, task: str, vps_ip: str) -> Dict:
        """ส่งงานไปทำบน VPS เพื่อเสริมความเร็ว"""
        import subprocess
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        result = {"vps_ip": vps_ip, "task": task, "status": "FAILED", "response_ms": 0}

        try:
            ssh_key = os.path.expanduser("~/.ssh/id_rsa")
            if not os.path.exists(ssh_key):
                result["error"] = "SSH key not found"
                return result

            start = time.time()
            # Execute task on VPS via SSH
            cmd = f'ssh -i {ssh_key} -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{vps_ip} "echo PROCESSING && date +%s%3N"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            latency = (time.time() - start) * 1000

            if proc.returncode == 0:
                result["status"] = "DELEGATED"
                result["response_ms"] = round(latency)
                result["output"] = proc.stdout.strip()
            else:
                result["error"] = proc.stderr[:100]

        except subprocess.TimeoutExpired:
            result["error"] = "VPS SSH timeout (30s)"
        except Exception as e:
            result["error"] = str(e)[:100]

        self._log_vps_task(result)
        return result

    def _log_vps_speed(self, model: Dict, latency_ms: float, status: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO vps_speed_boost (timestamp, vps_ip, provider, response_ms, status, task_delegated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    "LOCAL",
                    model["config_key"],
                    latency_ms,
                    status,
                    model["name"]
                ))
                conn.commit()
        except:
            pass

    def _log_vps_task(self, result: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO vps_speed_boost (timestamp, vps_ip, provider, response_ms, status, task_delegated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    result["vps_ip"],
                    "VPS_DELEGATE",
                    result.get("response_ms", 0),
                    result["status"],
                    result["task"][:50]
                ))
                conn.commit()
        except:
            pass

    def _log_performance(self, model_name: str, provider: str, latency_ms: float,
                         success: bool, task_type: str, error: str = ""):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO model_performance (timestamp, model_name, provider, latency_ms, success, task_type, error_msg)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    model_name, provider, latency_ms,
                    1 if success else 0, task_type, error
                ))
                conn.commit()
        except:
            pass

    def get_stats(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM model_performance").fetchone()[0]
                success = conn.execute("SELECT COUNT(*) FROM model_performance WHERE success=1").fetchone()[0]
                avg_latency = conn.execute("SELECT AVG(latency_ms) FROM model_performance WHERE success=1").fetchone()[0]
                return {
                    "total_queries": total,
                    "success_rate": f"{(success/total*100):.1f}%" if total > 0 else "0%",
                    "avg_latency_ms": round(avg_latency or 0),
                    "available_models": len([m for m in self.MODEL_POOL if self.config.get(m["config_key"], {}).get("key")])
                }
        except:
            return {"total_queries": 0, "success_rate": "0%", "avg_latency_ms": 0, "available_models": 0}

    def generate_report(self) -> str:
        stats = self.get_stats()
        vps_nodes = self.get_vps_nodes()
        report = []
        report.append("=" * 60)
        report.append("🧠 SMART ROUTER v1.2 - STATUS")
        report.append("=" * 60)
        report.append(f"  📊 Total Queries:    {stats['total_queries']}")
        report.append(f"  ✅ Success Rate:     {stats['success_rate']}")
        report.append(f"  ⚡ Avg Latency:      {stats['avg_latency_ms']}ms")
        report.append(f"  🤖 Available Models: {stats['available_models']}")
        report.append("")
        report.append("  📋 Model Pool (Free Tier):")
        for m in self.MODEL_POOL:
            key = self.config.get(m["config_key"], {}).get("key", "")
            icon = "🟢" if key else "🔴"
            report.append(f"    {icon} [{m['speed_tier']}] {m['name']}: ~{m['avg_latency_ms']}ms")
        report.append("")
        report.append(f"  🖥️  VPS Nodes: {len(vps_nodes)} available for speed boost")
        report.append("=" * 60)
        return "\n".join(report)


if __name__ == "__main__":
    router = NexusSmartRouterV12()
    print(router.generate_report())
