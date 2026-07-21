import os
import json
import sqlite3
import asyncio
import httpx
from typing import Dict, Any, Optional


class NexusOmniAIPoolManager:
    def __init__(self, sd_card_path: str = "/workspace/ck-nexus/"):
        self.sd_card_path = sd_card_path
        self.db_path = os.path.join(self.sd_card_path, "nexus_system_sd.db")
        self.config_path = "/root/.ck-nexus/config.json"
        self._init_ai_pool_table()

    def _init_ai_pool_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_ai_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_identifier TEXT UNIQUE,
                    provider_platform TEXT,
                    avg_speed_ms INTEGER,
                    status TEXT
                )
            """)
            models_data = [
                ("google/gemini-2.5-flash:free", "OpenRouter", 1200, "ACTIVE_PRIMARY"),
                ("qwen/qwen-2.5-coder-32b-instruct:free", "OpenRouter", 2000, "ACTIVE_CODE_EXPERT"),
                ("mistralai/mistral-7b-instruct:free", "OpenRouter", 1500, "ACTIVE_FALLBACK"),
                ("google/gemma-2-9b-it:free", "OpenRouter", 1800, "ACTIVE_FALLBACK"),
            ]
            for model, provider, speed, status in models_data:
                conn.execute("""
                    INSERT OR IGNORE INTO active_ai_pool (model_identifier, provider_platform, avg_speed_ms, status)
                    VALUES (?, ?, ?, ?)
                """, (model, provider, speed, status))
            conn.commit()

    def _load_config(self) -> dict:
        with open(self.config_path, "r") as f:
            return json.load(f)

    def get_pool_status(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM active_ai_pool ORDER BY avg_speed_ms ASC").fetchall()
            return [dict(r) for r in rows]

    async def execute_distributed_ai_task(self, prompt: str, task_category: str = "general") -> str:
        config = self._load_config()
        models = self._select_models(task_category, config)

        for model_cfg in models:
            result = await self._try_model(model_cfg, prompt)
            if result and not result.startswith("⚠️"):
                self._log_task(model_cfg["model"], model_cfg["provider"], task_category, "SUCCESS")
                return result
            self._log_task(model_cfg["model"], model_cfg["provider"], task_category, "FAIL")

        return "⚠️ [OMNI POOL]: โมเดลทั้งหมดไม่พร้อมใช้งาน กรุณาตรวจสอบ API keys"

    def _select_models(self, task_category: str, config: dict) -> list:
        code_models = [
            {"model": "qwen/qwen-2.5-coder-32b-instruct:free", "url": "https://openrouter.ai/api/v1/chat/completions", "key": config.get("OPENROUTER_API_KEY") or config.get("openrouter", {}).get("key"), "provider": "OpenRouter"},
            {"model": "google/gemini-2.5-flash:free", "url": "https://openrouter.ai/api/v1/chat/completions", "key": config.get("OPENROUTER_API_KEY") or config.get("openrouter", {}).get("key"), "provider": "OpenRouter"},
        ]
        general_models = [
            {"model": "google/gemini-2.5-flash:free", "url": "https://openrouter.ai/api/v1/chat/completions", "key": config.get("OPENROUTER_API_KEY") or config.get("openrouter", {}).get("key"), "provider": "OpenRouter"},
            {"model": "mistralai/mistral-7b-instruct:free", "url": "https://openrouter.ai/api/v1/chat/completions", "key": config.get("OPENROUTER_API_KEY") or config.get("openrouter", {}).get("key"), "provider": "OpenRouter"},
            {"model": "google/gemma-2-9b-it:free", "url": "https://openrouter.ai/api/v1/chat/completions", "key": config.get("OPENROUTER_API_KEY") or config.get("openrouter", {}).get("key"), "provider": "OpenRouter"},
        ]
        if "code" in task_category.lower():
            return code_models + general_models
        return general_models

    async def _try_model(self, model_cfg: dict, prompt: str) -> Optional[str]:
        if not model_cfg["key"]:
            return None
        headers = {"Authorization": f"Bearer {model_cfg['key']}", "Content-Type": "application/json"}
        payload = {
            "model": model_cfg["model"],
            "messages": [
                {"role": "system", "content": "คุณคือ AI ผู้เชี่ยวชาญระดับองค์กร ตอบสั้น กระชับ ตรงประเด็น"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048,
            "temperature": 0.7,
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(model_cfg["url"], headers=headers, json=payload, timeout=30.0)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                return f"⚠️ [{res.status_code}]"
        except Exception as e:
            return f"⚠️ {str(e)[:50]}"

    def _log_task(self, model: str, provider: str, category: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO work_logs (timestamp, action, details, status)
                VALUES (datetime('now'), ?, ?, ?)
            """, (f"OMNI_POOL:{category}", f"Model: {model} via {provider}", status))
            conn.commit()

    async def deploy_ai_to_vps(self, vps_ip: str, vps_pass: str) -> str:
        config = self._load_config()
        setup_script = f"""#!/bin/bash
apt-get update -qq && apt-get install -y -qq python3-pip docker.io docker-compose git
pip3 install httpx fastapi uvicorn sqlite3
systemctl enable docker && systemctl start docker
mkdir -p /opt/ck-nexus-worker
cat > /opt/ck-nexus-worker/worker.py << 'PYEOF'
import httpx, json, sqlite3
from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health(): return {{"status": "alive", "node": "ck-nexus-worker"}}
@app.post("/compute")
async def compute(payload: dict):
    prompt = payload.get("prompt", "")
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.groq.com/openai/v1/chat/completions",
            headers={{"Authorization": "Bearer {config.get('GROQ_API_KEY') or config.get('groq', {}).get('key', '')}"}},
            json={{"model": "llama-3.1-8b-instant", "messages": [{{"role":"user","content":prompt}}], "max_tokens": 1024}},
            timeout=30.0)
        return {{"result": r.json()["choices"][0]["message"]["content"]}}
PYEOF
cd /opt/ck-nexus-worker && docker run -d -p 8000:8000 --name ck-worker python:3.11-slim bash -c "pip install httpx fastapi uvicorn && uvicorn worker:app --host 0.0.0.0 --port 8000"
echo "DONE"
"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "sshpass", "-p", vps_pass, "ssh", "-o", "StrictHostKeyChecking=no",
                f"root@{vps_ip}", setup_script,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode()
            if "DONE" in output:
                return f"✅ AI Worker deployed on {vps_ip}"
            return f"⚠️ Deploy issue: {stderr.decode()[:200]}"
        except Exception as e:
            return f"⚠️ SSH failed: {str(e)[:100]}"
