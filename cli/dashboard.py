#!/usr/bin/env python3
"""CK-NEXUS Web Dashboard - simple HTTP server"""
import http.server
import json
import os
import sys
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_engine import NexusEngine

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CK-NEXUS AI OS</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0a0f; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        h1 { color: #00d4ff; font-size: 2em; }
        .subtitle { color: #888; margin-top: 5px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: #1a1a2e; border-radius: 10px; padding: 20px; border: 1px solid #333; }
        .card h2 { color: #00d4ff; margin-bottom: 15px; font-size: 1.2em; }
        .status-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; }
        .status-ok { color: #00ff88; }
        .status-error { color: #ff4444; }
        .status-warn { color: #ffaa00; }
        .chat-container { background: #1a1a2e; border-radius: 10px; padding: 20px; border: 1px solid #333; }
        #chat-messages { height: 400px; overflow-y: auto; margin-bottom: 15px; padding: 10px; background: #0a0a0f; border-radius: 5px; }
        .msg { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .msg-user { background: #1e3a5f; text-align: right; }
        .msg-ai { background: #2d1f3d; }
        .msg-meta { font-size: 0.8em; color: #888; margin-top: 5px; }
        .input-row { display: flex; gap: 10px; }
        #chat-input { flex: 1; padding: 12px; background: #0a0a0f; border: 1px solid #333; border-radius: 5px; color: #fff; font-size: 1em; }
        button { padding: 12px 24px; background: #00d4ff; color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        button:hover { background: #00b8d4; }
        .loading { color: #888; text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CK-NEXUS AI OS</h1>
            <div class="subtitle">Enterprise AI Operating System v0.1.0</div>
        </header>

        <div class="grid">
            <div class="card">
                <h2>System Status</h2>
                <div id="system-status">Loading...</div>
            </div>
            <div class="card">
                <h2>AI Providers</h2>
                <div id="provider-status">Loading...</div>
            </div>
            <div class="card">
                <h2>Memory</h2>
                <div id="memory-stats">Loading...</div>
            </div>
        </div>

        <div class="chat-container">
            <h2 style="margin-bottom: 15px; color: #00d4ff;">Chat with CK-NEXUS</h2>
            <div id="chat-messages">
                <div class="msg msg-ai">
                    <div>Welcome to CK-NEXUS AI OS. How can I help you?</div>
                </div>
            </div>
            <div class="input-row">
                <input type="text" id="chat-input" placeholder="Type your message..." onkeypress="if(event.key==='Enter')sendMessage()">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        async function loadStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                // System status
                document.getElementById('system-status').innerHTML = `
                    <div class="status-item"><span>Sessions</span><span>${data.stats.total_sessions}</span></div>
                    <div class="status-item"><span>Messages</span><span>${data.stats.total_messages}</span></div>
                    <div class="status-item"><span>Knowledge</span><span>${data.stats.total_knowledge}</span></div>
                    <div class="status-item"><span>Facts</span><span>${data.stats.total_facts}</span></div>
                    <div class="status-item"><span>Plugins</span><span>${data.stats.plugins}</span></div>
                `;

                // Provider status
                let providerHtml = '';
                for (const [name, info] of Object.entries(data.providers)) {
                    const cls = info.configured ? 'status-ok' : 'status-error';
                    providerHtml += `<div class="status-item"><span>${name}</span><span class="${cls}">${info.configured ? '✓' : '✗'}</span></div>`;
                }
                document.getElementById('provider-status').innerHTML = providerHtml;

                // Memory stats
                document.getElementById('memory-stats').innerHTML = `
                    <div class="status-item"><span>Tokens Used</span><span>${data.stats.total_tokens}</span></div>
                    <div class="status-item"><span>Skills</span><span>${data.stats.total_skills}</span></div>
                    <div class="status-item"><span>Commands</span><span>${data.stats.commands}</span></div>
                `;
            } catch (e) {
                console.error('Failed to load status:', e);
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            if (!msg) return;

            const messagesDiv = document.getElementById('chat-messages');
            messagesDiv.innerHTML += `<div class="msg msg-user"><div>${escapeHtml(msg)}</div></div>`;
            input.value = '';
            messagesDiv.innerHTML += `<div class="loading" id="loading">Thinking...</div>`;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await res.json();

                document.getElementById('loading')?.remove();

                if (data.error) {
                    messagesDiv.innerHTML += `<div class="msg msg-ai"><div style="color:#ff4444">Error: ${escapeHtml(data.error)}</div></div>`;
                } else {
                    let meta = [];
                    if (data.provider) meta.push(data.provider);
                    if (data.model) meta.push(data.model);
                    if (data.tokens) meta.push(data.tokens + 't');
                    messagesDiv.innerHTML += `<div class="msg msg-ai"><div>${escapeHtml(data.response)}</div><div class="msg-meta">[${meta.join(', ')}]</div></div>`;
                }
            } catch (e) {
                document.getElementById('loading')?.remove();
                messagesDiv.innerHTML += `<div class="msg msg-ai"><div style="color:#ff4444">Connection error</div></div>`;
            }

            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        loadStatus();
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>"""

class NexusHandler(http.server.BaseHTTPRequestHandler):
    engine = None

    def log_message(self, format, *args):
        pass  # Suppress logs

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif self.path == "/api/status":
            self.send_json({
                "stats": self.engine.memory.get_stats(),
                "providers": self.engine.router.get_status(),
                "session": self.engine.session_id,
                "plugins": self.engine.plugins.list_all(),
                "commands": list(self.engine.commands.commands.keys())
            })
        elif self.path == "/api/providers":
            self.send_json(self.engine.router.get_status())
        elif self.path == "/api/history":
            self.send_json({"history": self.engine.memory.get_history(self.engine.session_id)})
        elif self.path == "/api/sessions":
            self.send_json({"sessions": self.engine.memory.get_all_sessions()})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            msg = body.get("message", "")
            if msg:
                result = self.engine.process_input(msg)
                self.send_json(result)
            else:
                self.send_json({"error": "No message provided"})
        else:
            self.send_error(404)

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

def run_dashboard(port=8080):
    NexusHandler.engine = NexusEngine()
    server = http.server.HTTPServer(("0.0.0.0", port), NexusHandler)
    print(f"CK-NEXUS Dashboard: http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        NexusHandler.engine.shutdown()
        server.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_dashboard(port)
