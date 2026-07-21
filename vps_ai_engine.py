#!/usr/bin/env python3
"""
CK-NEXUS v1.2 - VPS AI Engine
Local AI on VPS - No External API Dependency
Uses SQLite knowledge base + Pattern matching for responses
"""

import os
import time
import json
import sqlite3
import re
from typing import Dict, List, Optional


class VPSAIEngine:
    """Local AI Engine - Runs on VPS without external API"""

    def __init__(self, sd_path: str = "/workspace/ck-nexus"):
        self.sd_path = sd_path
        self.db_path = os.path.join(sd_path, "nexus_system_sd.db")
        self._init_knowledge_base()

    def _init_knowledge_base(self):
        """สร้าง Knowledge Base ใน SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    keyword TEXT,
                    response TEXT,
                    confidence REAL DEFAULT 0.8,
                    source TEXT DEFAULT 'local',
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_conversation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    source TEXT,
                    input_text TEXT,
                    output_text TEXT,
                    method TEXT,
                    confidence REAL
                )
            """)
            conn.commit()
            self._seed_knowledge()

    def _seed_knowledge(self):
        """เติมความรู้พื้นฐาน"""
        knowledge = [
            ("greeting", "สวัสดี|hello|hi|หวัดดี|hey", "👋 สวัสดีครับ! ผม Dragon AI ผู้ช่วย CK-NEXUS v1.2\nเชื่อมต่อ VPS 6 ตัว พร้อมรับคำสั่ง 24 ชม.ครับ!", 0.95, "seed"),
            ("greeting", "อรุณสวัสดิ์|good morning", "🌅 อรุณสวัสดิ์ครับ! วันนี้พร้อมทำงานแล้วครับ!", 0.9, "seed"),
            ("identity", "ใคร|ชื่ออะไร|who are you|name", "🤖 ผม Dragon AI พัฒนาโดย CK-NEXUS v1.2\nเป็นผู้ช่วย AI ที่เชื่อมต่อกับ VPS Cluster 6 ตัว\nพูดไทยได้คล่อง ตอบเร็ว 389ms ครับ!", 0.95, "seed"),
            ("status", "สถานะ|status|สุขภาพ|health", self._get_status_response, 0.9, "seed"),
            ("vps", "vps|เซิร์ฟเวอร์|server|เครื่อง", self._get_vps_response, 0.9, "seed"),
            ("n8n", "n8n|automation|อัตโนมัติ|workflow", "🔧 n8n เป็นระบบ workflow automation ฟรี\nติดตั้งบน VPS ผ่าน Docker\nเชื่อมต่อ API ได้นับร้อย ไม่มีค่าใช้จ่าย\n\nปัจจุบันยังรอ IP/VPS จริงเพื่อ deploy", 0.85, "seed"),
            ("ai", "ai|ปัญญาประดิษฐ์|artificial intelligence|machine learning", "🧠 ระบบ AI ของเราใช้:\n- Groq Llama 3.3 70B (389ms)\n- OpenRouter Gemini 2.5 Flash\n- Smart Router สลับอัตโนมัติเมื่อพัง\n- Knowledge Base บน SQLite (22ms)", 0.9, "seed"),
            ("telegram", "telegram|บอท|bot|line", "📱 Dragon AI Bot:\n@dragon_ai_2026_bot\nเชื่อมต่อ Telegram 24 ชม.\nสั่งงานได้ทุกที่ผ่านมือถือ!", 0.95, "seed"),
            ("backup", "backup|สำรอง|ข้อมูล|database", "💾 ระบบสำรองข้อมูล:\n- Auto-backup ทุก 300 รอบ\n- Mirror sync ข้ามคลาวด์\n- SQLite on SD Card (22ms)\n- Zip archive + rsync", 0.85, "seed"),
            ("help", "ช่วย|help|คำสั่ง|command", self._get_help_response, 0.95, "seed"),
            ("thanks", "ขอบคุณ|thanks|thank you|ขอบใจ", "🙏 ยินดีครับ! มีอะไรให้ช่วยอีกบอกได้เลยนะครับ!", 0.9, "seed"),
            ("joke", "ตลก|joke|เรื่องตลก|ขำ", "😄 มีเรื่องเล่า:\nทำไม程序员 ชอบดื่มกาแฟ?\nเพราะ debugging ต้องใช้ความคิด!\n\n☕ 555+ ครับ!", 0.7, "seed"),
            ("time", "เวลา|time|กี่โมง|clock", lambda: f"🕐 เวลาปัจจุบัน: {time.strftime('%H:%M:%S')}\n📅 วันที่: {time.strftime('%Y-%m-%d')}", 0.95, "seed"),
            ("weather", "อากาศ|weather|ฝน|แดด", "🌤️ สำหรับสภาพอากาศ กรุณาบอก location ครับ\nหรือพิมพ์ 'สถานะระบบ' ดูข้อมูลแทนได้!", 0.7, "seed"),
            ("code", "โค้ด|code|โปรแกรม|python|javascript", "💻 ฉันช่วยเรื่องโค้ดได้!\n- Python, JavaScript, Bash\n- ระบบอัตโนมัติ\n- Docker, n8n workflow\n\nบอกหัวข้อที่ต้องการได้เลย!", 0.85, "seed"),
        ]

        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute("SELECT COUNT(*) FROM ai_knowledge").fetchone()[0]
            if existing < 10:
                for cat, keyword, resp, conf, src in knowledge:
                    if callable(resp):
                        resp = resp()
                    conn.execute("""
                        INSERT OR IGNORE INTO ai_knowledge (category, keyword, response, confidence, source, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (cat, keyword, resp, conf, src, time.strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()

    def _get_status_response(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                vps = conn.execute("SELECT COUNT(*) FROM autonomous_vps_servers").fetchone()[0]
                ideas = conn.execute("SELECT COUNT(*) FROM external_ideas_bank").fetchone()[0]
                bp = conn.execute("SELECT COUNT(*) FROM execution_blueprints").fetchone()[0]
                faults = conn.execute("SELECT COUNT(*) FROM system_fault_logs WHERE timestamp > datetime('now', '-24 hours')").fetchone()[0]
            return f"📊 CK-NEXUS v1.2 STATUS\n━━━━━━━━━━━━━━━━━━\n🖥️ VPS: {vps} nodes\n💡 Ideas: {ideas}\n🧠 Blueprints: {bp}\n🚨 Faults (24h): {faults}\n⚡ Cache: 22ms | Groq: 389ms"
        except:
            return "⚠️ ไม่สามารถดึงสถานะได้"

    def _get_vps_response(self) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT provider_name, status FROM autonomous_vps_servers").fetchall()
            text = "🖥️ VPS CLUSTER\n━━━━━━━━━━━━━━━━━━\n"
            for name, status in rows:
                icon = "🟢" if "ACTIVE" in status else "🔴"
                text += f"{icon} {name}\n"
            return text
        except:
            return "⚠️ ไม่สามารถดึงข้อมูล VPS ได้"

    def _get_help_response(self) -> str:
        return """🐉 DRAGON AI COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━
📊 สถานะ - ดูสถานะระบบ
🖥️ VPS - ดู VPS ทั้งหมด
💡 ไอเดีย - ดูไอเดียที่收集ได้
🧠 สถิติ - ดูสถิติ AI Router
📱 Telegram - ข้อมูลบอท
🔧 n8n - ระบบ automation
💻 โค้ด - ช่วยเขียนโค้ด
━━━━━━━━━━━━━━━━━━━━━━━
💬 ถามอะไรก็ได้เลยครับ!"""

    # ═══════════════════════════════════════════════════════
    # LOCAL AI PROCESSING (No API needed)
    # ═══════════════════════════════════════════════════════
    def process_locally(self, user_input: str) -> Optional[str]:
        """ประมวลผลคำสั่งในเครื่อง ไม่ต้องพึ่ง API"""
        input_lower = user_input.lower().strip()

        # Search knowledge base
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT keyword, response, confidence FROM ai_knowledge").fetchall()

        best_match = None
        best_score = 0

        for keywords, response, confidence in rows:
            keyword_list = keywords.split("|")
            for kw in keyword_list:
                if kw.lower() in input_lower or input_lower in kw.lower():
                    if confidence > best_score:
                        best_score = confidence
                        best_match = response

        if best_match and best_score > 0.7:
            if callable(best_match):
                best_match = best_match()
            self._log_ai_usage(user_input, best_match, "local_kb", best_score)
            return best_match

        # Pattern matching for complex queries
        response = self._pattern_match(input_lower)
        if response:
            self._log_ai_usage(user_input, response, "pattern_match", 0.8)
            return response

        return None

    def _pattern_match(self, text: str) -> Optional[str]:
        """จับรูปแบบข้อความที่ซับซ้อน"""
        # Question patterns
        if text.startswith(("ทำไม", "ทำไม่", "why")):
            return "🤔 นั่นเป็นคำถามที่ดีเลยครับ! ให้ผมค้นข้อมูลเพิ่มเติมก่อนนะ..."
        elif text.startswith(("ทำยังไง", "how", "วิธี")):
            return "💡 ผมมีคำแนะนำครับ ลองพิมพ์ 'ช่วย' เพื่อดูคำสั่งทั้งหมด"
        elif text.startswith(("ที่ไหน", "where")):
            return "📍 ข้อมูลอยู่บน VPS Cluster 6 ตัว ทั้ง Oracle, Google, Kamatera ฯลฯ ครับ!"
        elif "กี่" in text:
            return "🔢 ให้ผมดึงข้อมูลตัวเลขล่าสุดก่อนนะ... พิมพ์ 'สถานะ' ดูรายละเอียดได้เลย!"
        elif any(kw in text for kw in ["รัก", "love", "like"]):
            return "❤️ ผมก็รักคุณเหมือนกันครับ! พร้อมทำงานให้เสมอ!"
        elif any(kw in text for kw in ["เบื่อ", "bored", "เหงา"]):
            return "😤 อย่าเบื่อสิครับ! มาคุยเรื่องเทคกันดีกว่า AI, VPS, n8n มีเรื่องคุยเยอะเลย!"
        elif any(kw in text for kw in ["งง", "confuse", "ไม่เข้าใจ"]):
            return "🤷 ไม่ต้องงงครับ! ผมอธิบายใหม่ได้ พิมพ์มาได้เลยว่าไม่เข้าใจตรงไหน"
        elif any(kw in text for kw in ["เก่ง", "good", "ดี", "เจ๋ง", "cool"]):
            return "😊 ขอบคุณครับ! ผมพยายามเต็มที่เพื่อช่วยคุณเสมอ!"
        return None

    def _log_ai_usage(self, input_text: str, output_text: str, method: str, confidence: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO ai_conversation_log (timestamp, source, input_text, output_text, method, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (time.strftime("%Y-%m-%d %H:%M:%S"), "local", input_text[:200], output_text[:200], method, confidence))
                conn.commit()
        except:
            pass

    def learn_from_conversation(self, keyword: str, response: str, category: str = "learned"):
        """เรียนรู้จากบทสนทนาใหม่"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO ai_knowledge (category, keyword, response, confidence, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (category, keyword, response, 0.8, "conversation_learned", time.strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
        except:
            pass

    def get_stats(self) -> Dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM ai_knowledge").fetchone()[0]
                conversations = conn.execute("SELECT COUNT(*) FROM ai_conversation_log").fetchone()[0]
                avg_conf = conn.execute("SELECT AVG(confidence) FROM ai_conversation_log").fetchone()[0]
                return {
                    "knowledge_entries": total,
                    "total_conversations": conversations,
                    "avg_confidence": round(avg_conf or 0, 2)
                }
        except:
            return {"knowledge_entries": 0, "total_conversations": 0, "avg_confidence": 0}

    def generate_report(self) -> str:
        stats = self.get_stats()
        report = []
        report.append("=" * 50)
        report.append("🤖 VPS AI ENGINE - STATUS")
        report.append("=" * 50)
        report.append(f"  📚 Knowledge Base:  {stats['knowledge_entries']} entries")
        report.append(f"  💬 Conversations:   {stats['total_conversations']}")
        report.append(f"  🎯 Avg Confidence:  {stats['avg_confidence']}")
        report.append(f"  ⚡ Method:          Local SQLite (22ms)")
        report.append(f"  🔌 API Required:    NO")
        report.append("=" * 50)
        return "\n".join(report)


if __name__ == "__main__":
    engine = VPSAIEngine()
    print(engine.generate_report())

    # Test conversations
    tests = ["สวัสดี", "ใคร", "สถานะ", "vps", "ช่วย", "เวลา", "ขอบคุณ"]
    print("\n🧪 TEST RESPONSES:")
    for t in tests:
        resp = engine.process_locally(t)
        print(f"  [{t}] -> {resp[:60]}...")
