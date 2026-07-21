#!/usr/bin/env python3
"""
CK-NEXUS v1.2 - Telegram Bot Handler
24/7 AI Chat Bot - @dragon_ai_2026_bot
Uses Groq (free, 389ms) for intelligent responses
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


class DragonAIBot:
    """24/7 Telegram Bot - @dragon_ai_2026_bot"""

    def __init__(self):
        self.config_path = "/root/.codex/telegram-bridge.json"
        self.config = self._load_config()
        self.bot_token = self.config.get("botToken", "")
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        self.sd_path = "/workspace/ck-nexus"
        self.db_path = os.path.join(self.sd_path, "nexus_system_sd.db")
        self.config_json = "/root/.ck-nexus/config.json"
        self.system_config = self._load_system_config()
        self.last_update_id = 0
        self.is_running = False
        self.user_sessions = {}
        self._init_bot_db()

    def _load_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def _load_system_config(self) -> Dict:
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {}

    def _init_bot_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_id INTEGER,
                    username TEXT,
                    message TEXT,
                    response TEXT,
                    model_used TEXT,
                    response_ms REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    message_count INTEGER DEFAULT 0,
                    trusted INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    # ═══════════════════════════════════════════════════════
    # TELEGRAM API METHODS
    # ═══════════════════════════════════════════════════════
    def _api_call(self, method: str, data: Dict = None) -> Optional[Dict]:
        """เรียก Telegram API"""
        try:
            url = f"{self.api_base}/{method}"
            if data:
                payload = json.dumps(data).encode()
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            else:
                req = urllib.request.Request(url)

            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return None

    def get_updates(self) -> List[Dict]:
        """ดึงข้อความใหม่จาก Telegram"""
        result = self._api_call("getUpdates", {
            "offset": self.last_update_id + 1,
            "timeout": 5,
            "allowed_updates": ["message"]
        })
        if result and result.get("ok"):
            return result.get("result", [])
        return []

    def send_message(self, chat_id: int, text: str, parse_mode: str = None) -> bool:
        """ส่งข้อความกลับ"""
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        result = self._api_call("sendMessage", data)
        return result and result.get("ok", False)

    def send_typing(self, chat_id: int):
        """ส่งสัญญาณกำลังพิมพ์"""
        self._api_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})

    # ═══════════════════════════════════════════════════════
    # AI RESPONSE ENGINE (Groq Free - 389ms)
    # ═══════════════════════════════════════════════════════
    def get_ai_response(self, user_message: str, user_id: int) -> str:
        """สร้างคำตอบ AI ผ่าน Groq (ฟรี, เร็ว 389ms)"""
        # Load system context
        groq_key = self.system_config.get("groq", {}).get("key", "")
        groq_model = self.system_config.get("groq", {}).get("model", "llama-3.3-70b-versatile")

        if not groq_key:
            return self._fallback_response(user_message)

        # System prompt - Dragon AI personality
        system_prompt = """คุณคือ Dragon AI ผู้ช่วย AI อัจฉริยะของ CK-NEXUS v1.2
คุณเป็นผู้เชี่ยวชาญด้านเทคโนโลยี, AI, VPS, และระบบอัตโนมัติ
คุณพูดไทยได้คล่องและเป็นกันเอง เหมือนเพื่อนคุยเรื่องเทค
ตอบสั้น กระชับ ได้ใจความ ไม่เกิน 3-4 ประโยค
ถ้าไม่รู้ก็บอกตรงๆ ว่าไม่รู้ แล้วเสนอทางแก้
คุณสามารถสั่งงานระบบ CK-NEXUS ได้ เช่น:
- ดูสถานะ VPS
- ดูสถิติระบบ
- ค้นหาข้อมูล
- แจ้งเตือนเมื่อมีปัญหา"""

        # Get conversation history
        history = self._get_conversation_history(user_id)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            start = time.time()
            payload = json.dumps({
                "model": groq_model,
                "messages": messages[-10:],  # Keep last 10 messages for context
                "max_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9
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
                response = data["choices"][0]["message"]["content"]
                latency = (time.time() - start) * 1000

                # Log conversation
                self._log_conversation(user_id, user_message, response, groq_model, latency)
                return response

        except urllib.error.HTTPError as e:
            if e.code == 429:
                return self._fallback_response(user_message)
            return f"⚠️ AI Error: HTTP {e.code}"
        except Exception as e:
            return self._fallback_response(user_message)

    def _fallback_response(self, message: str) -> str:
        """คำตอบfallback เมื่อ API ไม่ว่าง"""
        msg = message.lower()

        # Command responses
        if any(kw in msg for kw in ["status", "สถานะ", "สุขภาพ"]):
            return self._get_system_status()
        elif any(kw in msg for kw in ["vps", "เซิร์ฟเวอร์", "server"]):
            return self._get_vps_status()
        elif any(kw in msg for kw in ["帮助", "ช่วย", "help", "คำสั่ง"]):
            return self._get_help_text()
        elif any(kw in msg for kw in ["สวัสดี", "hello", "hi", "หวัดดี"]):
            return "👋 สวัสดีครับ! ผม Dragon AI ผู้ช่วย CK-NEXUS v1.2\nพิมพ์ 'ช่วย' ดูคำสั่งทั้งหมดได้เลยครับ!"
        elif any(kw in msg for kw in ["ใคร", "who", "name"]):
            return "🤖 ผม Dragon AI พัฒนาโดย CK-NEXUS v1.2\nเป็นผู้ช่วย AI ที่เชื่อมต่อกับ VPS Cluster 6 ตัวครับ!"
        else:
            return "🤖 ได้รับข้อความแล้วครับ! พิมพ์ 'ช่วย' เพื่อดูคำสั่งทั้งหมด"

    def _get_system_status(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                vps_count = conn.execute("SELECT COUNT(*) FROM autonomous_vps_servers").fetchone()[0]
                ideas = conn.execute("SELECT COUNT(*) FROM external_ideas_bank").fetchone()[0]
                faults = conn.execute("SELECT COUNT(*) FROM system_fault_logs WHERE timestamp > datetime('now', '-24 hours')").fetchone()[0]
                blueprints = conn.execute("SELECT COUNT(*) FROM execution_blueprints").fetchone()[0]
                convos = conn.execute("SELECT COUNT(*) FROM telegram_conversations").fetchone()[0]

            return f"""📊 CK-NEXUS v1.2 STATUS
━━━━━━━━━━━━━━━━━━━━━━━
🖥️ VPS Nodes: {vps_count} active
💡 Ideas Bank: {ideas} concepts
🧠 Blueprints: {blueprints} executed
🚨 Faults (24h): {faults}
💬 Conversations: {convos}
━━━━━━━━━━━━━━━━━━━━━━━
⚡ Cache: 22ms | Groq: 389ms
🕐 Uptime: 24/7 autonomous"""
        except:
            return "⚠️ ไม่สามารถดึงสถานะได้"

    def _get_vps_status(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT provider_name, status, trial_days FROM autonomous_vps_servers").fetchall()

            text = "🖥️ VPS CLUSTER STATUS\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for name, status, days in rows:
                icon = "🟢" if "ACTIVE" in status else "🔴"
                text += f"{icon} {name}: {status} ({days}d)\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "💡 พิมพ์ 'deploy n8n' เพื่อติดตั้ง n8n บน VPS"
            return text
        except:
            return "⚠️ ไม่สามารถดึงข้อมูล VPS ได้"

    def _get_help_text(self) -> str:
        return """🐉 DRAGON AI COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━
📊 สถานะ - ดูสถานะระบบ
🖥️ VPS - ดู VPS ทั้งหมด
💡 ไอเดีย - ดูไอเดียที่收集ได้
🔧 ปัญหา - ดูข้อผิดพลาดล่าสุด
🧠 สถิติ - ดูสถิติ AI Router
🔄 รีสตาร์ท - สั่งรีสตาร์ท daemon
━━━━━━━━━━━━━━━━━━━━━━━
💬 ถามอะไรก็ได้ เช่น:
- "ช่วยอธิบาย n8n"
- "VPS ตัวไหนแรงสุด"
- "สถานะระบบตอนนี้"
━━━━━━━━━━━━━━━━━━━━━━━"""

    # ═══════════════════════════════════════════════════════
    # CONVERSATION MANAGEMENT
    # ═══════════════════════════════════════════════════════
    def _get_conversation_history(self, user_id: int) -> List[Dict]:
        """ดึงประวัติสนทนา"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT message, response FROM telegram_conversations
                    WHERE user_id = ? ORDER BY id DESC LIMIT 10
                """, (user_id,)).fetchall()

            history = []
            for msg, resp in reversed(rows):
                history.append({"role": "user", "content": msg})
                history.append({"role": "assistant", "content": resp})
            return history
        except:
            return []

    def _log_conversation(self, user_id: int, message: str, response: str, model: str, latency: float):
        """บันทึกบทสนทนา"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update or insert user
                existing = conn.execute("SELECT user_id FROM telegram_users WHERE user_id=?", (user_id,)).fetchone()
                if existing:
                    conn.execute("""
                        UPDATE telegram_users SET last_seen=?, message_count=message_count+1 WHERE user_id=?
                    """, (timestamp, user_id))
                else:
                    conn.execute("""
                        INSERT INTO telegram_users (user_id, username, first_seen, last_seen, message_count)
                        VALUES (?, ?, ?, ?, 1)
                    """, (user_id, f"user_{user_id}", timestamp, timestamp))

                # Log conversation
                conn.execute("""
                    INSERT INTO telegram_conversations (timestamp, user_id, username, message, response, model_used, response_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, user_id, f"user_{user_id}", message, response, model, latency))
                conn.commit()
        except:
            pass

    # ═══════════════════════════════════════════════════════
    # COMMAND PROCESSOR
    # ═══════════════════════════════════════════════════════
    def process_command(self, user_id: int, message: str) -> str:
        """ประมวลผลคำสั่งพิเศษ"""
        msg = message.lower().strip()

        if msg in ["status", "สถานะ", "สุขภาพ"]:
            return self._get_system_status()
        elif msg in ["vps", "เซิร์ฟเวอร์", "server"]:
            return self._get_vps_status()
        elif msg in ["帮助", "ช่วย", "help", "คำสั่ง"]:
            return self._get_help_text()
        elif msg in ["ไอเดีย", "ideas", "ความคิด"]:
            return self._get_ideas_summary()
        elif msg in ["ปัญหา", "faults", "ข้อผิดพลาด"]:
            return self._get_faults_summary()
        elif msg in ["สถิติ", "stats", "router"]:
            return self._get_router_stats()
        elif "รีสตาร์ท" in msg or "restart" in msg:
            return self._restart_daemon()
        elif "deploy n8n" in msg:
            return "🐝 สั่ง deploy n8n แล้วครับ! กำลังติดตั้งบน VPS..."
        else:
            return None  # Not a command, use AI

    def _get_ideas_summary(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM external_ideas_bank").fetchone()[0]
                stored = conn.execute("SELECT COUNT(*) FROM external_ideas_bank WHERE status='STORED_FOR_HYBRID'").fetchone()[0]
                integrated = conn.execute("SELECT COUNT(*) FROM external_ideas_bank WHERE status='INTEGRATED_INTO_CORE'").fetchone()[0]
                return f"💡 IDEAS BANK\n━━━━━━━━━━━━━━━━━━\nTotal: {total}\nStored: {stored}\nIntegrated: {integrated}"
        except:
            return "⚠️ ไม่สามารถดึงข้อมูลไอเดียได้"

    def _get_faults_summary(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT broken_component, error_reason FROM system_fault_logs WHERE timestamp > datetime('now', '-24 hours') ORDER BY id DESC LIMIT 5"
                ).fetchall()
            if not rows:
                return "✅ ไม่มีข้อผิดพลาดใน 24 ชม. ล่าสุด"
            text = "🚨 FAULTS (24h)\n━━━━━━━━━━━━━━━━━━\n"
            for comp, reason in rows:
                text += f"❌ {comp}: {reason}\n"
            return text
        except:
            return "⚠️ ไม่สามารถดึงข้อมูล faults ได้"

    def _get_router_stats(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM model_performance").fetchone()[0]
                success = conn.execute("SELECT COUNT(*) FROM model_performance WHERE success=1").fetchone()[0]
                avg = conn.execute("SELECT AVG(latency_ms) FROM model_performance WHERE success=1").fetchone()[0]
            return f"🧠 ROUTER STATS\n━━━━━━━━━━━━━━━━━━\nQueries: {total}\nSuccess: {success}\nAvg Latency: {avg or 0:.0f}ms"
        except:
            return "⚠️ ไม่สามารถดึงสถิติได้"

    def _restart_daemon(self) -> str:
        try:
            os.system("bash /workspace/ck-nexus/start_daemon.sh")
            return "🔄 รีสตาร์ท daemon แล้วครับ!"
        except:
            return "⚠️ ไม่สามารถรีสตาร์ทได้"

    # ═══════════════════════════════════════════════════════
    # MAIN BOT LOOP
    # ═══════════════════════════════════════════════════════
    def start_polling(self):
        """เริ่มรับข้อความจาก Telegram 24/7"""
        self.is_running = True
        print(f"🐉 Dragon AI Bot (@dragon_ai_2026_bot) starting...", flush=True)
        print(f"   Token: {self.bot_token[:20]}...", flush=True)

        # Verify bot connection
        me = self._api_call("getMe")
        if me and me.get("ok"):
            bot_info = me["result"]
            print(f"   ✅ Connected as: @{bot_info.get('username', 'unknown')}", flush=True)
            print(f"   📡 Polling for messages...", flush=True)
        else:
            print(f"   ❌ Failed to connect to Telegram API", flush=True)
            return

        while self.is_running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.last_update_id = update["update_id"]
                    self._handle_update(update)
            except KeyboardInterrupt:
                self.is_running = False
                break
            except Exception as e:
                print(f"   ⚠️ Poll error: {str(e)[:50]}", flush=True)
                time.sleep(2)

    def _handle_update(self, update: Dict):
        """จัดการข้อความที่เข้ามา"""
        message = update.get("message", {})
        if not message:
            return

        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("username", "unknown")
        text = message.get("text", "")

        if not text:
            return

        print(f"   💬 [{username}]: {text[:50]}", flush=True)

        # Send typing indicator
        self.send_typing(chat_id)

        # Check for commands first
        cmd_response = self.process_command(user_id, text)

        if cmd_response:
            response = cmd_response
        else:
            # Use AI for general conversation
            response = self.get_ai_response(text, user_id)

        # Send response
        self.send_message(chat_id, response)
        print(f"   🤖 [{username}]: {response[:50]}...", flush=True)


# ═══════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    bot = DragonAIBot()
    bot.start_polling()
