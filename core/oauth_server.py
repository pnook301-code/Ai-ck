"""OAuth2 Callback Server with state validation"""
import http.server
import json
import threading
import urllib.parse
import secrets
from datetime import datetime


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    auth_code = None
    auth_state = None
    auth_error = None
    expected_state = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/callback":
            if "code" in params:
                returned_state = params.get("state", [None])[0]

                if OAuthCallbackHandler.expected_state:
                    if not secrets.compare_digest(OAuthCallbackHandler.expected_state or "", returned_state or ""):
                        OAuthCallbackHandler.auth_error = "State mismatch - possible CSRF attack"
                        OAuthCallbackHandler.auth_code = None
                        self._send_error_page()
                        return

                OAuthCallbackHandler.auth_code = params["code"][0]
                OAuthCallbackHandler.auth_state = returned_state
                OAuthCallbackHandler.auth_error = None
                self._send_success_page()
            elif "error" in params:
                OAuthCallbackHandler.auth_error = params.get("error_description", ["Unknown error"])[0]
                OAuthCallbackHandler.auth_code = None
                self._send_error_page()
            else:
                OAuthCallbackHandler.auth_error = "No code or error in callback"
                self._send_error_page()
        elif parsed.path == "/health":
            self._send_json({"status": "ok", "time": datetime.now().isoformat()})
        else:
            self._send_index_page()

    def _send_success_page(self):
        code = OAuthCallbackHandler.auth_code
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CK-NEXUS Auth</title>
<style>
body{{font-family:system-ui;background:#0a0a0f;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
.card{{background:#1a1a2e;padding:40px;border-radius:15px;border:1px solid #333;max-width:500px;text-align:center}}
h1{{color:#00ff88}}.code{{background:#0a0a0f;padding:15px;border-radius:8px;font-family:monospace;color:#00ff88;margin:15px 0;word-break:break-all}}
</style></head>
<body><div class="card">
<h1>&#10003; Authorization Successful</h1>
<p>CK-NEXUS has been authorized to access LINE.</p>
<div class="code">{code}</div>
<p>Copy the code above and return to CK-NEXUS.</p>
<p>Run: <strong>/line code={code}</strong></p>
</div></body></html>"""
        self._send_html(html)

    def _send_error_page(self):
        error = OAuthCallbackHandler.auth_error or "Unknown error"
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CK-NEXUS Auth Error</title>
<style>
body{{font-family:system-ui;background:#0a0a0f;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
.card{{background:#1a1a2e;padding:40px;border-radius:15px;border:1px solid #333;max-width:500px;text-align:center}}
h1{{color:#ff4444}}
</style></head>
<body><div class="card">
<h1>&#10007; Authorization Failed</h1>
<p>{error}</p>
<p>Please try again from CK-NEXUS.</p>
</div></body></html>"""
        self._send_html(html)

    def _send_index_page(self):
        html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CK-NEXUS OAuth</title>
<style>
body{font-family:system-ui;background:#0a0a0f;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.card{background:#1a1a2e;padding:40px;border-radius:15px;border:1px solid #333;max-width:500px;text-align:center}
h1{color:#00d4ff}
</style></head>
<body><div class="card">
<h1>CK-NEXUS OAuth Server</h1>
<p>Waiting for LINE authorization callback...</p>
</div></body></html>"""
        self._send_html(html)

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


class OAuthServer:
    MAX_REQUEST_SIZE = 1024 * 10  # 10KB limit

    def __init__(self, port=8088):
        self.port = port
        self.server = None
        self.thread = None

    def start(self, expected_state=None):
        OAuthCallbackHandler.expected_state = expected_state
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.auth_error = None
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), OAuthCallbackHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.thread = None

    def get_code(self):
        return OAuthCallbackHandler.auth_code

    def get_error(self):
        return OAuthCallbackHandler.auth_error

    def is_ready(self):
        return OAuthCallbackHandler.auth_code is not None

    def has_error(self):
        return OAuthCallbackHandler.auth_error is not None

    def reset(self):
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.auth_state = None
        OAuthCallbackHandler.auth_error = None
        OAuthCallbackHandler.expected_state = None
