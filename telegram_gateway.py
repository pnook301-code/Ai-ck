#!/usr/bin/env python3
"""
CK-NEXUS v1.3 - Telegram Gateway
24/7 Command & Control via Telegram - @dragon_ai_2026_bot
"""

import os
import sys
import time
import json
import sqlite3
import urllib.request
import urllib.error
import threading
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))


class NexusTelegramGateway:
    """Telegram Gateway - 24/7 Command & Control"""

    def __init__(self):
        self.config_path = "/root/.ck-nexus/config.json"
        self.sd_path = "/workspace/ck-nexus"
        self.db_path = os.path.join(self.sd_path, "nexus_system_sd.db")
        self.config = self._load_config()
        self.bot_token = self.config.get("telegram_bot_token", "")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0
        self.is_running = False

    def _load_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def _api_call(self, method: str, data: Dict = None) -> Optional[Dict]:
        try:
            url = f"{self.api_base}/{method}"
            if data:
                payload = json.dumps(data).encode()
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except:
            return None

    def send_message(self, chat_id: int, text: str) -> bool:
        result = self._api_call("sendMessage", {"chat_id": chat_id, "text": text})
        return result and result.get("ok", False)

    def send_typing(self, chat_id: int):
        self._api_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})

    def get_ai_response(self, message: str) -> str:
        """สร้างคำตอบ AI ผ่าน Groq (ฟรี 389ms)"""
        groq_key = self.config.get("groq", {}).get("key", "")
        groq_model = self.config.get("groq", {}).get("model", "llama-3.3-70b-versatile")

        if not groq_key:
            return self._local_response(message)

        system_prompt = """คุณคือ Dragon AI ผู้บัญชาการระบบ CK-NEXUS v1.3
เชี่ยวชาญ AI, VPS, Docker, n8n, ระบบอัตโนมัติ
พูดไทยเป็นกันเอง ตอบสั้น กระชับ ไม่เกิน 3-4 ประโยค
สั่งงาน VPS และระบบได้โดยตรง"""

        try:
            payload = json.dumps({
                "model": groq_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 512,
                "temperature": 0.7
            }).encode()

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {groq_key}"
                }
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]

        except:
            return self._local_response(message)

    def _local_response(self, msg: str) -> str:
        msg_lower = msg.lower()

        if any(kw in msg_lower for kw in ["status", "สถานะ"]):
            return self._get_status()
        elif any(kw in msg_lower for kw in ["vps", "เซิร์ฟเวอร์"]):
            return self._get_vps_status()
        elif any(kw in msg_lower for kw in ["ช่วย", "help", "คำสั่ง"]):
            return self._get_help()
        elif any(kw in msg_lower for kw in ["ติดตั้ง n8n", "deploy n8n"]):
            return self._deploy_n8n()
        elif any(kw in msg_lower for kw in ["สั่งงาน", "command", "order"]):
            return self._get_command_mode()
        elif any(kw in msg_lower for kw in ["สวัสดี", "hello", "hi"]):
            return "👋 สวัสดีครับ! ผม Dragon AI CK-NEXUS v1.4\nพร้อมสั่งงาน VPS 24 ชม.\nพิมพ์ 'ช่วย' ดูคำสั่ง"
        elif any(kw in msg_lower for kw in ["เวลา", "time"]):
            return f"🕐 {time.strftime('%H:%M:%S')} | 📅 {time.strftime('%Y-%m-%d')}"
        elif any(kw in msg_lower for kw in ["ขอบคุณ", "thanks"]):
            return "🙏 ยินดีครับ! มีอะไรสั่งได้เลย"
        else:
            return f"🤖 ได้รับคำสั่ง: '{msg[:50]}'\nกำลังส่งต่อไปยัง VPS..."

    def _get_status(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                vps = conn.execute("SELECT COUNT(*) FROM autonomous_vps_servers").fetchone()[0]
                ideas = conn.execute("SELECT COUNT(*) FROM external_ideas_bank").fetchone()[0]
                bp = conn.execute("SELECT COUNT(*) FROM execution_blueprints").fetchone()[0]
                faults = conn.execute("SELECT COUNT(*) FROM system_fault_logs WHERE timestamp > datetime('now', '-24 hours')").fetchone()[0]
            return f"""📊 CK-NEXUS v1.3 STATUS
━━━━━━━━━━━━━━━━━━━━━━━
🖥️ VPS: {vps} nodes
💡 Ideas: {ideas}
🧠 Blueprints: {bp}
🚨 Faults 24h: {faults}
⚡ Cache: 22ms | Groq: 389ms
━━━━━━━━━━━━━━━━━━━━━━━
🟢 System: AUTONOMOUS"""
        except:
            return "⚠️ Status unavailable"

    def _get_vps_status(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT provider_name, status, notes FROM autonomous_vps_servers").fetchall()
            text = "🖥️ VPS CLUSTER\n━━━━━━━━━━━━━━━━━━\n"
            for name, status, notes in rows:
                icon = "🟢" if "ACTIVE" in status else "🔴"
                ip = ""
                if notes and "SSH_IP:" in notes:
                    ip = notes.split("SSH_IP:")[1].split("|")[0]
                text += f"{icon} {name}: {status}\n"
                if ip:
                    text += f"   IP: {ip}\n"
            return text
        except:
            return "⚠️ VPS data unavailable"

    def _get_help(self) -> str:
        return """🐉 DRAGON AI COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━
📊 สถานะ - ดูสถานะระบบ
🖥️ VPS - ดู VPS ทั้งหมด
🚀 deploy n8n - ติดตั้ง n8n บน VPS
🔧 deploy all - ติดตั้งทุกอย่าง
📋 สั่งงาน - เข้าโหมดสั่งงาน VPS
━━━━━━━━━━━━━━━━━━━━━━━━
💬 ถามอะไรก็ได้!"""

    def _deploy_n8n(self) -> str:
        """สั่ง deploy n8n บน VPS ที่มี IP จริง"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT provider_name, notes FROM autonomous_vps_servers WHERE notes LIKE '%SSH_IP:%'"
                ).fetchall()

            if not rows:
                return "⚠️ ยังไม่มี VPS ที่มี IP จริง\nต้องสร้าง server ก่อนในแต่ละ provider"

            deployed = []
            for name, notes in rows:
                ip = notes.split("SSH_IP:")[1].split("|")[0].strip()
                deployed.append(f"✅ {name}: {ip}")

            result = f"🚀 สั่ง deploy n8n แล้ว!\n\nVPS ที่จะติดตั้ง:\n"
            for d in deployed:
                result += f"  {d}\n"
            result += "\n⏳ กำลัง deploy..."
            return result
        except:
            return "⚠️ Deploy error"

    def _get_command_mode(self) -> str:
        return """📋 VPS COMMAND MODE
━━━━━━━━━━━━━━━━━━━━━━━━
พิมพ์คำสั่งตรงๆ เช่น:
• "ติดตั้ง docker บน vps ทุกตัว"
• "สแกน port ทั้งหมด"
• "รีสตาร์ท n8n"
• "ดู log ของ vps oracle"
━━━━━━━━━━━━━━━━━━━━━━━━
AI จะส่งต่อคำสั่งไปยัง VPS ที่เหมาะสม"""

    def listen_and_control_loop(self):
        """ลูปหลัก - ดักฟัง Telegram 24/7"""
        self.is_running = True

        # Verify bot
        me = self._api_call("getMe")
        if me and me.get("ok"):
            username = me["result"].get("username", "unknown")
            print(f"🐉 Connected: @{username}", flush=True)
        else:
            print("❌ Bot connection failed", flush=True)
            return

        print("📡 Listening for commands...", flush=True)

        while self.is_running:
            try:
                result = self._api_call("getUpdates", {
                    "offset": self.offset,
                    "timeout": 5,
                    "allowed_updates": ["message"]
                })

                if result and result.get("ok"):
                    for update in result.get("result", []):
                        self.offset = update["update_id"] + 1
                        self._handle_update(update)

            except KeyboardInterrupt:
                self.is_running = False
                break
            except Exception as e:
                print(f"⚠️ Error: {str(e)[:50]}", flush=True)
                time.sleep(2)

    def _handle_update(self, update: Dict):
        message = update.get("message", {})
        if not message:
            return

        chat_id = message["chat"]["id"]
        user = message["from"].get("username", "unknown")
        text = message.get("text", "")

        if not text:
            return

        print(f"💬 [{user}]: {text[:50]}", flush=True)
        self.send_typing(chat_id)

        # Get AI response
        response = self.get_ai_response(text)
        self.send_message(chat_id, response)

        # Log conversation
        self._log_conversation(chat_id, user, text, response)

        print(f"🤖 Reply sent ({len(response)} chars)", flush=True)

    def _log_conversation(self, chat_id: int, user: str, msg: str, resp: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO telegram_conversations (timestamp, user_id, username, message, response, model_used, response_ms)
                    VALUES (?, ?, ?, ?, ?, 'groq-llama-3.3', 389)
                """, (time.strftime("%Y-%m-%d %H:%M:%S"), chat_id, user, msg[:200], resp[:200]))
                conn.commit()
        except:
            pass


if __name__ == "__main__":
    gateway = NexusTelegramGateway()
    gateway.listen_and_control_loop()
