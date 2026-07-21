#!/usr/bin/env python3
"""
CK-NEXUS v0.8-CYBER - CLI Mode
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(__file__))

from auto_system import get_system

system = get_system()

HELP = """
╔══════════════════════════════════════════════════════════════╗
║      ⚡ CK-NEXUS v0.8-CYBER - COMMANDS                      ║
╠══════════════════════════════════════════════════════════════╣
║  🌐 OS AGENT                                                ║
║    เปิดเว็บ <site>    - Open website (youtube/github/etc)   ║
║    รันคำสั่ง <cmd>    - Run terminal command                 ║
║    สถานะเครื่อง       - Server status                        ║
║    列出ไฟล์ <path>    - List files                           ║
║    โปรเซส             - Show processes                       ║
║                                                              ║
║  💬 CHAT                                                     ║
║    <message>           - Chat with AI (streaming)            ║
║    /sync <message>    - Chat without streaming               ║
║                                                              ║
║  📊 SYSTEM                                                   ║
║    /status             - System status                       ║
║    /cache              - Cache statistics                    ║
║    /help               - Show commands                       ║
║    /quit               - Exit                                ║
╚══════════════════════════════════════════════════════════════╝
"""

async def chat_async(msg: str):
    """Stream chat response"""
    print("🤖 ", end="", flush=True)
    async for token in system.chat_stream(msg):
        print(token, end="", flush=True)
    print()

def main():
    print("⚡ CK-NEXUS v0.8-CYBER - เริ่มทำงานแล้ว!")
    print(system.status())

    while True:
        try:
            user_input = input("\033[92mCYBER>\033[0m ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
                print("👋 ลาก่อน!")
                break

            if user_input.lower() in ("/help", "help"):
                print(HELP)
                continue

            if user_input.lower() == "/status":
                print(system.status())
                continue

            if user_input.lower() == "/cache":
                stats = system.cache.stats()
                print(f"📦 Cache: {stats['entries']} entries | {stats['hits']} hits | {stats['logs']} logs")
                continue

            if user_input.lower().startswith("/sync "):
                msg = user_input[6:].strip()
                result = system.chat_sync(msg)
                print(f"🤖 [{result.get('provider', '?')}] {result.get('latency_ms', 0)}ms")
                print(f"   {result['response']}")
                continue

            # Default: streaming chat
            asyncio.run(chat_async(user_input))

        except (KeyboardInterrupt, EOFError):
            print("\n👋 ลาก่อน!")
            break


if __name__ == "__main__":
    main()
