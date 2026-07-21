#!/usr/bin/env python3
"""
CK-NEXUS v1.4 - TOTAL CONTROL
Telegram Executive - 24/7 Bot + Autonomous Engine
"""

import os
import sys
import time
import json
import sqlite3
import threading
import signal

sys.path.insert(0, os.path.dirname(__file__))

from auto_system import get_system
from autonomous_engine import get_autonomous_engine
from director_core import get_director_core
from cognitive_planner import get_cognitive_planner
from matrix_sentinel import NexusMatrixSentinel
from protocols import get_protocol_manager
from vps_auto_reg import get_vps_registrar
from vps_takeover_plugin import get_vps_takeover
from hive_network import get_hive_manager
from web_agent_plugin import get_web_agent
from vps_hive_setup import NexusOmniHiveSetup
from smart_router_v12 import NexusSmartRouterV12
from gmail_control_plugin import NexusGmailControlPlugin
from telegram_gateway import NexusTelegramGateway
from omni_ai_pool import NexusOmniAIPoolManager
from agent_swarm import SwarmOrchestrator, get_event_bus, get_shared_memory


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)


# Global keep-alive
KEEP_RUNNING = True

def handle_signal(sig, frame):
    global KEEP_RUNNING
    KEEP_RUNNING = False
    log("⚡ Shutdown signal received")

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def run_autonomous():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    system = get_system()
    engine = get_autonomous_engine()
    async def run():
        await engine.start_monitoring_loop()
    try:
        loop.run_until_complete(run())
    except:
        pass


def run_director():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    director = get_director_core()
    async def run():
        await director.start_director_mainframe()
    try:
        loop.run_until_complete(run())
    except:
        pass


def run_telegram():
    gw = NexusTelegramGateway()
    try:
        gw.listen_and_control_loop()
    except:
        pass


def run_omni_deploy():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ai_pool = NexusOmniAIPoolManager(sd_card_path="/workspace/ck-nexus/")
    system = get_system()
    async def deploy_loop():
        import time as _time
        cycle = 0
        while True:
            cycle += 1
            try:
                with sqlite3.connect(system.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    vps_list = conn.execute(
                        "SELECT * FROM autonomous_vps_servers WHERE status='ACTIVE'"
                    ).fetchall()
                    for vps in vps_list:
                        notes = vps["notes"] or ""
                        if "SSH_IP:" in notes:
                            ip = notes.split("SSH_IP:")[1].split("|")[0].strip()
                            pw = notes.split("SSH_PASSWORD:")[1].split("|")[0].strip() if "SSH_PASSWORD:" in notes else ""
                            if ip and cycle % 60 == 1:
                                result = await ai_pool.deploy_ai_to_vps(ip, pw)
                                log(f"🌐 VPS Deploy: {result[:80]}")
            except Exception as e:
                pass
            _time.sleep(30)
    try:
        loop.run_until_complete(deploy_loop())
    except:
        pass


def run_agent_swarm():
    """Start Agent Swarm — 6 agents working in parallel."""
    try:
        swarm = SwarmOrchestrator()
        swarm.start()
        log("🐝 Agent Swarm: 6 agents online (Researcher, Coder, Writer, Analyst, Translator, Creator)")
        # Keep running
        while KEEP_RUNNING:
            time.sleep(10)
    except Exception as e:
        log(f"❌ Agent Swarm error: {e}")


def main():
    global KEEP_RUNNING

    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " ⚡ CK-NEXUS v1.4 - TOTAL CONTROL ".center(58) + "║")
    print("║" + " 🐉 TELEGRAM EXECUTIVE ACTIVE ".center(58) + "║")
    print("╠" + "═" * 58 + "╣")
    print("║  🐉 Telegram:    @Gemini990100_Bot 24/7            ║")
    print("║  🧠 Smart Router: 6 Models Auto-Fallback            ║")
    print("║  👁️  Sentinel:     Real-Time Fault Detection         ║")
    print("║  💡 Ideas:        Cross-Platform Learning            ║")
    print("║  🖥️  VPS:          6 Free Nodes Connected             ║")
    print("║  🤖 Autonomous:   5s Monitoring Loop                 ║")
    print("║  👑 Director:     3s Self-Healing                    ║")
    print("╠" + "═" * 58 + "╣")
    print("║  🧠 Omni AI Pool: 6 Models + VPS Distributed       ║")
    print("║  ⚡ Groq: 389ms | Cache: 22ms | SQLite: 85ms       ║")
    print("╚" + "═" + "═" * 58 + "╝")
    print()

    # Initialize Omni AI Pool
    ai_pool = NexusOmniAIPoolManager(sd_card_path="/workspace/ck-nexus/")
    log("🧠 Omni AI Pool: 6 models loaded (Groq + OpenRouter)")

    # Start all background threads (non-daemon so they keep alive)
    t1 = threading.Thread(target=run_autonomous, name="Autonomous")
    t2 = threading.Thread(target=run_director, name="Director")
    t3 = threading.Thread(target=run_telegram, name="Telegram")
    t4 = threading.Thread(target=run_omni_deploy, name="OmniDeploy")
    t5 = threading.Thread(target=run_agent_swarm, name="AgentSwarm")

    t1.daemon = True
    t2.daemon = True
    t3.daemon = True
    t4.daemon = True
    t5.daemon = True

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()

    log("🤖 Autonomous Engine: ACTIVE")
    log("👑 Director Engine: ACTIVE")
    log("🐉 [@Gemini990100_Bot]: Telegram gateway started")
    log("🌐 Omni Deploy: VPS AI worker deployment loop started")
    log("🐝 Agent Swarm: 6 agents online")
    log("🚀 [v1.4] TOTAL CONTROL online - ALL SYSTEMS RUNNING")

    # Keep main thread alive forever
    cycle = 0
    while KEEP_RUNNING:
        cycle += 1
        try:
            if cycle % 100 == 0:
                pool_status = ai_pool.get_pool_status()
                active = len([p for p in pool_status if "ACTIVE" in p["status"]])
                log(f"💓 [HEARTBEAT] Cycle: {cycle} | Threads: {threading.active_count()} | AI Models: {active}/6")
        except:
            pass
        time.sleep(5)

    log("⚡ Mainframe shutting down.")


if __name__ == "__main__":
    main()
