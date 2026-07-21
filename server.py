#!/usr/bin/env python3
"""
CK-NEXUS v0.9-DIRECTOR - Ultimate Autonomous Server
"""

import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.dirname(__file__))

from auto_system import get_system
from autonomous_engine import get_autonomous_engine
from director_core import get_director_core

try:
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, StreamingResponse
    from pydantic import BaseModel
    import uvicorn

    auto_engine = get_autonomous_engine()
    director = get_director_core()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start all autonomous systems
        auto_task = asyncio.create_task(auto_engine.start_monitoring_loop())
        director_task = asyncio.create_task(director.start_director_mainframe())
        print("🤖 [AUTONOMOUS ENGINE]: Background monitoring active")
        print("👑 [DIRECTOR ENGINE]: Autonomous control engaged")
        yield
        auto_engine.stop()
        director.shutdown()
        auto_task.cancel()
        director_task.cancel()

    app = FastAPI(title="CK-NEXUS v0.9-DIRECTOR", lifespan=lifespan)
    system = get_system()

    class ChatRequest(BaseModel):
        message: str

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return """
        <html>
        <head>
            <title>⚡ CK-NEXUS v0.9: DIRECTOR MAINFRAME ⚡</title>
            <style>
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body { font-family: 'Courier New', monospace; background: #050508; color: #00ffcc; padding: 20px; }
                .container { max-width: 1000px; margin: auto; border: 2px solid #ff0055; background: rgba(15, 15, 25, 0.95); padding: 25px; border-radius: 4px; box-shadow: 0 0 30px #ff0055; }
                h1 { text-align: center; font-size: 26px; color: #ff0055; text-shadow: 0 0 15px #ff0055; letter-spacing: 4px; border-bottom: 2px dashed #00ffcc; padding-bottom: 12px; }
                .subtitle { text-align: center; color: #666; font-size: 11px; margin-bottom: 15px; }
                #chat-box { height: 320px; overflow-y: auto; background: #030305; border: 1px solid #00ffcc; padding: 15px; border-radius: 2px; margin-bottom: 15px; box-shadow: inset 0 0 15px rgba(0,255,204,0.15); }
                .msg { margin-bottom: 8px; padding: 6px 10px; border-radius: 3px; font-size: 13px; line-height: 1.5; }
                .user { color: #ff0055; border-left: 3px solid #ff0055; background: rgba(255,0,85,0.05); }
                .ai { color: #00ffcc; border-left: 3px solid #00ffcc; background: rgba(0,255,204,0.03); }
                .os { color: #ffaa00; border-left: 3px solid #ffaa00; background: rgba(255,170,0,0.05); }
                .director { color: #aa00ff; border-left: 3px solid #aa00ff; background: rgba(170,0,255,0.05); }
                .sentinel { color: #ff3333; border-left: 3px solid #ff3333; background: rgba(255,50,50,0.05); }
                .input-area { display: flex; gap: 10px; }
                input { flex: 1; padding: 12px; background: #0a0a14; border: 1px solid #ff0055; color: #00ffcc; font-family: inherit; font-size: 14px; outline: none; }
                input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.3); }
                button { padding: 12px 25px; background: #ff0055; color: #fff; font-weight: bold; font-family: inherit; border: none; cursor: pointer; text-transform: uppercase; letter-spacing: 1px; }
                button:hover { background: #00ffcc; color: #000; }
                .panels { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px; }
                .panel { background: #09090e; border: 1px dashed; padding: 12px; border-radius: 2px; }
                .panel.system { border-color: #00ffcc; }
                .panel.director { border-color: #aa00ff; }
                .panel.sentinel { border-color: #ff3333; }
                .panel-title { font-weight: bold; margin-bottom: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; }
                pre { margin: 0; font-size: 11px; line-height: 1.4; white-space: pre-wrap; max-height: 120px; overflow-y: auto; }
                .system .panel-title { color: #00ffcc; }
                .director .panel-title { color: #aa00ff; }
                .sentinel .panel-title { color: #ff3333; }
                .system pre { color: #34d399; }
                .director pre { color: #cc66ff; }
                .sentinel pre { color: #ff6666; }
                ::-webkit-scrollbar { width: 5px; }
                ::-webkit-scrollbar-thumb { background: #ff0055; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚡ CK-NEXUS V0.9: DIRECTOR MAINFRAME ⚡</h1>
                <p class="subtitle">Autonomous Director + Sentinel + Self-Healing + Agent Dispatcher</p>
                
                <div id="chat-box">
                    <div class="director msg"><b>[DIRECTOR]:</b> ระบบผู้บัญชาการสูงสุดพร้อมควบคุม สั่งการ และซ่อมแซมตัวเองอัตโนมัติ</div>
                    <div class="sentinel msg"><b>[SENTINEL]:</b> Proactive Failure Detection ACTIVE - ตรวจจับก่อนระบบพังจริง</div>
                    <div class="ai msg"><b>[SYSTEM]:</b> Drop .json in autonomous_jobs/ เพื่อให้ AI จัดการอัตโนมัติ</div>
                </div>
                
                <div class="input-area">
                    <input type="text" id="user-input" placeholder="ENTER COMMAND..." onkeypress="if(event.key==='Enter')send()">
                    <button onclick="send()">EXECUTE</button>
                </div>
                
                <div class="panels">
                    <div class="panel system">
                        <div class="panel-title">📊 SYSTEM STATUS</div>
                        <pre id="sys-status">LOADING...</pre>
                    </div>
                    <div class="panel director">
                        <div class="panel-title">👑 DIRECTOR LOGS</div>
                        <pre id="dir-logs">LOADING...</pre>
                    </div>
                    <div class="panel sentinel">
                        <div class="panel-title">🛡️ SENTINEL ALERTS</div>
                        <pre id="sen-logs">LOADING...</pre>
                    </div>
                </div>
            </div>
            <script>
                async function refresh() {
                    try {
                        const [s, d, se] = await Promise.all([
                            fetch('/api/status').then(r=>r.json()),
                            fetch('/api/director/logs').then(r=>r.json()),
                            fetch('/api/sentinel/logs').then(r=>r.json())
                        ]);
                        document.getElementById('sys-status').innerText = s.status;
                        
                        let dText = '';
                        (d.logs||[]).slice(0,6).forEach(l => {
                            const i = l.status==='ok'?'✅':l.status==='warning'?'⚠️':'❌';
                            dText += i+' ['+l.timestamp.slice(11,19)+'] '+l.action.slice(0,30)+'\\n';
                        });
                        document.getElementById('dir-logs').innerText = dText || 'No logs';
                        
                        let sText = '';
                        (se.logs||[]).slice(0,6).forEach(l => {
                            const i = l.status==='ok'?'✅':'⚠️';
                            sText += i+' ['+l.timestamp.slice(11,19)+'] '+l.action.slice(0,30)+'\\n';
                        });
                        document.getElementById('sen-logs').innerText = sText || 'All clear';
                    } catch(e) {}
                }
                async function send() {
                    const inp = document.getElementById('user-input');
                    const msg = inp.value.trim();
                    if(!msg) return;
                    const box = document.getElementById('chat-box');
                    box.innerHTML += '<div class="user msg">▶ '+msg+'</div>';
                    inp.value = '';
                    const rid = 'r-'+Date.now();
                    box.innerHTML += '<div class="ai msg" id="'+rid+'">⏳</div>';
                    box.scrollTop = box.scrollHeight;
                    try {
                        const res = await fetch('/api/chat-stream?message='+encodeURIComponent(msg));
                        const reader = res.body.getReader();
                        const dec = new TextDecoder();
                        const el = document.getElementById(rid);
                        el.innerText = '';
                        while(true) {
                            const {done, value} = await reader.read();
                            if(done) break;
                            const chunk = dec.decode(value, {stream:true});
                            if(chunk.includes('[OS AGENT]')||chunk.includes('[TERMINAL]')) el.className='os msg';
                            if(chunk.includes('[DIRECTOR]')) el.className='director msg';
                            if(chunk.includes('[SENTINEL]')) el.className='sentinel msg';
                            el.innerText += chunk;
                            box.scrollTop = box.scrollHeight;
                        }
                    } catch(e) { document.getElementById(rid).innerText='Error: '+e.message; }
                    refresh();
                }
                refresh();
                setInterval(refresh, 8000);
            </script>
        </body>
        </html>
        """

    @app.get("/api/chat-stream")
    async def api_chat_stream(message: str):
        return StreamingResponse(system.chat_stream(message), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/chat")
    async def api_chat(req: ChatRequest):
        return system.chat_sync(req.message)

    @app.get("/api/status")
    async def api_status():
        return {"status": system.status()}

    @app.get("/api/director/logs")
    async def api_director_logs():
        return {"logs": director.get_logs(20)}

    @app.get("/api/director/stats")
    async def api_director_stats():
        return director.get_stats()

    @app.get("/api/sentinel/logs")
    async def api_sentinel_logs():
        return {"logs": director.get_logs(20)}

    @app.get("/api/autonomous/stats")
    async def api_auto_stats():
        return auto_engine.get_stats()

except ImportError as e:
    print(f"⚠️ Missing: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("⚡ CK-NEXUS v0.9-DIRECTOR starting...")
    print("👑 Director Engine: ACTIVE")
    print("🤖 Autonomous Engine: ACTIVE")
    print("🛡️ Sentinel: ACTIVE")
    uvicorn.run(app, host="127.0.0.1", port=8000)
