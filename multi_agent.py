#!/usr/bin/env python3
"""
CK-NEXUS Multi-Agent System
AI ตัวที่ 1: นายช่าง (Creator) - สร้างงาน
AI ตัวที่ 2: ผู้ตรวจ (Critic) - จับผิดและสั่งแก้
รันจนกว่างานจะสมบูรณ์ 10/10
"""

import os
import sys
import json
import sqlite3
import urllib.request
from datetime import datetime

SD_PATH = "/workspace/ck-nexus"
CONFIG_PATH = "/root/.ck-nexus/config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def call_ai(prompt: str, json_mode: bool = False) -> str:
    """Call AI model (OpenRouter primary, Groq fallback)"""
    config = load_config()
    openrouter_key = config.get("openrouter", {}).get("key", "")
    groq_key = config.get("groq", {}).get("key", "")

    # Try OpenRouter free models first
    models = [
        {"name": "google/gemma-4-26b-a4b-it:free", "key": openrouter_key, "url": "https://openrouter.ai/api/v1/chat/completions"},
        {"name": "nvidia/nemotron-3-super-120b-a12b:free", "key": openrouter_key, "url": "https://openrouter.ai/api/v1/chat/completions"},
        {"name": "google/gemma-4-31b-it:free", "key": openrouter_key, "url": "https://openrouter.ai/api/v1/chat/completions"},
        {"name": "llama-3.1-8b-instant", "key": groq_key, "url": "https://api.groq.com/openai/v1/chat/completions"},
    ]

    for model in models:
        if not model["key"]:
            continue
        try:
            payload = {
                "model": model["name"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.7,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            req = urllib.request.Request(
                model["url"],
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {model['key']}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            continue

    return "AI model ไม่พร้อมใช้งาน"


def creator_agent(task: str, feedback: str = "") -> str:
    """AI ตัวที่ 1: นายช่าง - สร้างสรรค์งาน"""
    prompt = f"""คุณคือ "AI นายช่าง (The Creator)" 
หน้าที่ของคุณคือสร้างสรรค์งานตามโจทย์ให้ดีที่สุด

โจทย์หลัก: {task}
"""
    if feedback:
        prompt += f"""
⚠️ มีคำสั่งแก้จากผู้ตรวจ: "{feedback}"
จงนำคำวิจารณ์นี้ไปปรับปรุงงานชิ้นเดิมให้ดีขึ้นและส่งกลับมาใหม่
"""
    prompt += "\nจงส่งงานที่สมบูรณ์ที่สุดออกมาเลย ไม่ต้องมีคำอธิบายอื่น"
    return call_ai(prompt)


def critic_agent(task: str, work: str) -> dict:
    """AI ตัวที่ 2: ผู้ตรวจการ - จับผิดและประเมิน"""
    prompt = f"""คุณคือ "AI ผู้ตรวจการ (The Critic)"
หน้าที่ของคุณคือจับผิด ตรวจสอบความถูกต้อง และประเมินงานอย่างเข้มงวด

โจทย์ดั้งเดิม: {task}

งานที่ส่งมาตรวจสอบ:
----------
{work}
----------

ตอบกลับเป็น JSON เท่านั้น:
{{"passed": true/false, "score": 1-10, "feedback": "คำวิจารณ์ภาษาไทย"}}"""
    return call_ai(prompt, json_mode=True)


def log_to_db(task: str, rounds: int, score: int, status: str):
    """บันทึกลงฐานข้อมูล"""
    db_path = os.path.join(SD_PATH, "nexus_system_sd.db")
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT INTO work_logs (timestamp, action, details, status)
                VALUES (datetime('now'), ?, ?, ?)
            """, (f"MULTI_AGENT: {task[:50]}", f"Rounds: {rounds}, Score: {score}/10", status))
            conn.commit()
    except:
        pass


def run_multi_agent(task: str, max_iterations: int = 3):
    """ระบบ Multi-Agent หลัก"""
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  🤖 CK-NEXUS MULTI-AGENT SYSTEM                 ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  🛠️  Agent 1: นายช่าง (Creator)                  ║")
    print("║  👁️  Agent 2: ผู้ตรวจ (Critic)                   ║")
    print("║  🔄 Loop: จนกว่างานจะสมบูรณ์ 10/10              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    current_work = ""
    feedback = ""
    history = []

    print(f"📝 โจทย์: {task}")
    print(f"🔄 จำนวนรอบสูงสุด: {max_iterations}")
    print()

    for i in range(1, max_iterations + 1):
        print(f"{'─' * 50}")
        print(f"🛠️  [รอบที่ {i}] นายช่าง (Creator) กำลังผลิตงาน...")
        
        current_work = creator_agent(task, feedback)
        print(f"🤖 [นายช่าง ส่งงาน]:")
        print(f"{current_work[:500]}{'...' if len(current_work) > 500 else ''}")
        print()

        print(f"🔍 ผู้ตรวจการ (Critic) กำลังสแกน...")
        
        try:
            raw_audit = critic_agent(task, current_work)
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw_audit)
            if json_match:
                audit = json.loads(json_match.group())
            else:
                audit = {"passed": False, "score": 5, "feedback": raw_audit}
        except Exception as e:
            audit = {"passed": False, "score": 5, "feedback": str(e)}

        score = audit.get("score", 0)
        passed = audit.get("passed", False)
        feedback_text = audit.get("feedback", "")

        print(f"📊 [ผลการตรวจ]: คะแนน {score}/10 | {'✅ ผ่าน' if passed else '❌ ต้องแก้'}")
        print(f"💬 [คำวิจารณ์]: {feedback_text}")
        print()

        history.append({
            "round": i,
            "work_preview": current_work[:200],
            "score": score,
            "passed": passed,
            "feedback": feedback_text
        })

        if passed:
            print(f"🎉 งานสำเร็จเสร็จสิ้นในรอบที่ {i}!")
            log_to_db(task, i, score, "SUCCESS")
            break

        feedback = feedback_text

        if i == max_iterations:
            print(f"⚠️ ครบโควตาการแก้ {max_iterations} รอบ ส่งมอบงานเวอร์ชันที่ดีที่สุด")
            log_to_db(task, i, score, "MAX_ITERATIONS")

    # Save final result
    result_path = os.path.join(SD_PATH, f"multi_agent_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(result_path, "w") as f:
        json.dump({
            "task": task,
            "final_work": current_work,
            "history": history,
            "total_rounds": len(history),
            "final_score": history[-1]["score"] if history else 0
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 บันทึกผลลัพธ์: {result_path}")
    print(f"{'═' * 50}")

    return current_work


def interactive_mode():
    """โหมด Interactive - รับโจทย์จากผู้ใช้"""
    print("🎯 พิมพ์โจทย์ที่ต้องการให้ AI ทำ (พิมพ์ 'exit' เพื่อออก)")
    print()
    
    while True:
        try:
            task = input("✍️  โจทย์: ").strip()
            if task.lower() in ['exit', 'quit', 'ออก']:
                print("👋 ลาก่อน!")
                break
            if not task:
                continue
            
            run_multi_agent(task)
            print()
        except KeyboardInterrupt:
            print("\n👋 ลาก่อน!")
            break


def auto_mode():
    """โหมด Auto - รันโจทย์อัตโนมัติ"""
    tasks = [
        "เขียนสคริปต์ Python สำหรับสแกนพอร์ตที่เปิดอยู่บนเซิร์ฟเวอร์",
        "คิดสโลแกนร้านกาแฟ 5 แบบ แนวคนรุ่นใหม่",
        "เขียน SQL query สำหรับหาลูกค้าที่ซื้อของมากที่สุด 10 อันดับ"
    ]
    
    for task in tasks:
        print(f"\n{'═' * 50}")
        print(f"📋 โจทย์ถัดไป: {task}")
        run_multi_agent(task)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "auto":
            auto_mode()
        elif sys.argv[1] == "task" and len(sys.argv) > 2:
            task = " ".join(sys.argv[2:])
            run_multi_agent(task)
        else:
            print("Usage:")
            print("  python3 multi_agent.py                    # Interactive mode")
            print("  python3 multi_agent.py auto               # Auto mode")
            print("  python3 multi_agent.py task [โจทย์]       # Run specific task")
    else:
        interactive_mode()
