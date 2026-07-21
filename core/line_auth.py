"""LINE OAuth2 Authentication - uses encrypted token storage"""
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import secrets
from datetime import datetime, timedelta

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class LineAuthManager:
    AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
    TOKEN_URL = "https://api.line.me/v2/oauth/accessToken"
    REVOKE_URL = "https://api.line.me/v2/oauth/revoke"
    VERIFY_URL = "https://api.line.me/v2/oauth/verify"
    PROFILE_URL = "https://api.line.me/v2/profile"

    SCOPES = [
        "profile", "openid", "email",
        "message.send", "message.write",
        "offline_access"
    ]

    def __init__(self, credentials_dir=None):
        self.credentials_dir = credentials_dir or os.path.expanduser("~/.ck-nexus/credentials")
        os.makedirs(self.credentials_dir, exist_ok=True)
        self.token_file = os.path.join(self.credentials_dir, "line_tokens.json")
        self.state_file = os.path.join(self.credentials_dir, "line_state.json")
        self.key_file = os.path.join(self.credentials_dir, ".line_key")
        self._fernet = self._init_fernet()
        self.credentials = self._load_credentials()

    def _init_fernet(self):
        if not HAS_CRYPTO:
            return None
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
        return Fernet(key)

    def _encrypt(self, data):
        if not self._fernet:
            return data
        return self._fernet.encrypt(json.dumps(data).encode()).decode()

    def _decrypt(self, encrypted):
        if not self._fernet:
            return encrypted
        try:
            return json.loads(self._fernet.decrypt(encrypted.encode()).decode())
        except Exception:
            return None

    def _load_credentials(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file) as f:
                    data = json.load(f)
                decrypted = self._decrypt(data.get("encrypted", ""))
                if decrypted:
                    return decrypted
            except Exception:
                pass
        return {}

    def _save_credentials(self):
        encrypted = self._encrypt(self.credentials)
        with open(self.token_file, "w") as f:
            json.dump({"encrypted": encrypted, "updated_at": datetime.now().isoformat()}, f, indent=2)
        os.chmod(self.token_file, 0o600)

    def _save_state(self, state):
        with open(self.state_file, "w") as f:
            json.dump(state, f)

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                return json.load(f)
        return {}

    def generate_auth_url(self, channel_id, redirect_uri="http://localhost:8088/callback"):
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": channel_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "scope": " ".join(self.SCOPES),
            "prompt": "consent",
            "max_age": "3600",
            "ui_locales": "en",
            "bot_prompt": "aggressive"
        }

        self._save_state({
            "state": state,
            "nonce": nonce,
            "channel_id": channel_id,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now().isoformat()
        })

        auth_url = f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"
        return auth_url, state

    def validate_state(self, returned_state):
        saved = self._load_state()
        expected = saved.get("state", "")
        return secrets.compare_digest(expected, returned_state)

    def exchange_code(self, code, channel_id, channel_secret, redirect_uri="http://localhost:8088/callback"):
        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": channel_id,
            "client_secret": channel_secret
        }).encode()

        req = urllib.request.Request(self.TOKEN_URL, data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                self.credentials = {
                    "access_token": result["access_token"],
                    "expires_in": result.get("expires_in", 10368000),
                    "refresh_token": result.get("refresh_token", ""),
                    "token_type": result.get("token_type", "Bearer"),
                    "scope": result.get("scope", ""),
                    "channel_id": channel_id,
                    "obtained_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(seconds=result.get("expires_in", 10368000))).isoformat()
                }
                self._save_credentials()
                self._clear_state()
                return True, "Authentication successful"
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else str(e)
            return False, f"Token exchange failed: {body}"

    def refresh_access_token(self, channel_secret=None):
        if not self.credentials.get("refresh_token"):
            return False, "No refresh token available"

        secret = channel_secret
        if not secret:
            return False, "No channel secret provided"

        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.credentials["refresh_token"],
            "client_secret": secret
        }).encode()

        req = urllib.request.Request(self.TOKEN_URL, data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                self.credentials["access_token"] = result["access_token"]
                self.credentials["expires_in"] = result.get("expires_in", 10368000)
                self.credentials["expires_at"] = (datetime.now() + timedelta(seconds=result.get("expires_in", 10368000))).isoformat()
                if "refresh_token" in result:
                    self.credentials["refresh_token"] = result["refresh_token"]
                self.credentials["refreshed_at"] = datetime.now().isoformat()
                self._save_credentials()
                return True, "Token refreshed"
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else str(e)
            return False, f"Refresh failed: {body}"

    def verify_token(self):
        if not self.credentials.get("access_token"):
            return False, "No access token"

        req = urllib.request.Request(self.VERIFY_URL, headers={
            "Authorization": f"Bearer {self.credentials['access_token']}"
        })

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return True, {
                    "client_id": result.get("client_id", ""),
                    "expires_in": result.get("expires_in", 0),
                    "scope": result.get("scope", ""),
                    "token_type": result.get("token_type", "")
                }
        except urllib.error.HTTPError as e:
            return False, f"Verification failed: HTTP {e.code}"

    def get_profile(self):
        if not self.credentials.get("access_token"):
            return False, "No access token"

        req = urllib.request.Request(self.PROFILE_URL, headers={
            "Authorization": f"Bearer {self.credentials['access_token']}"
        })

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return True, {
                    "user_id": result.get("userId", ""),
                    "display_name": result.get("displayName", ""),
                    "picture_url": result.get("pictureUrl", ""),
                    "status_message": result.get("statusMessage", "")
                }
        except urllib.error.HTTPError as e:
            return False, f"Profile fetch failed: HTTP {e.code}"

    def revoke_token(self, channel_secret=None):
        if not self.credentials.get("access_token"):
            return False, "No access token"

        secret = channel_secret
        if not secret:
            return False, "No channel secret"

        data = urllib.parse.urlencode({
            "client_id": self.credentials.get("channel_id", ""),
            "client_secret": secret,
            "access_token": self.credentials["access_token"]
        }).encode()

        req = urllib.request.Request(self.REVOKE_URL, data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.credentials = {}
                self._save_credentials()
                return True, "Token revoked"
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return False, f"Revoke failed: {body}"

    def logout(self):
        self.credentials = {}
        self._save_credentials()
        return True, "Logged out"

    def is_expired(self):
        if not self.credentials.get("expires_at"):
            return True
        try:
            expires = datetime.fromisoformat(self.credentials["expires_at"])
            return datetime.now() >= expires
        except Exception:
            return True

    def get_valid_token(self, channel_secret=None):
        if self.is_expired():
            if self.credentials.get("refresh_token") and channel_secret:
                ok, msg = self.refresh_access_token(channel_secret)
                if ok:
                    return self.credentials.get("access_token"), "Refreshed"
                return None, msg
            return None, "Token expired"
        return self.credentials.get("access_token"), "OK"

    def _clear_state(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    def get_status(self):
        has_token = bool(self.credentials.get("access_token"))
        return {
            "configured": has_token,
            "authenticated": has_token,
            "expired": self.is_expired(),
            "has_refresh_token": bool(self.credentials.get("refresh_token")),
            "channel_id": self.credentials.get("channel_id", ""),
            "obtained_at": self.credentials.get("obtained_at", ""),
            "expires_at": self.credentials.get("expires_at", ""),
            "scope": self.credentials.get("scope", ""),
            "encrypted": HAS_CRYPTO
        }
