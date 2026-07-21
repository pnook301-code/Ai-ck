#!/usr/bin/env python3
"""
CK-NEXUS v1.4 - Unified API Key Manager v2.0
Key Pool + Auto-Rotator + Health Monitor
จัดการ API Keys แบบมืออาชีพ: หลาย Key ต่อ Provider, สลับอัตโนมัติ, ตรวจสอบสุขภาพ
"""

import os
import json
import time
import hashlib
import asyncio
import sqlite3
import threading
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class KeyStatus(Enum):
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    ERROR = "error"
    EXHAUSTED = "exhausted"


@dataclass
class APIKey:
    id: str
    provider: str
    encrypted_key: str
    alias: str
    status: KeyStatus = KeyStatus.ACTIVE
    last_used: float = 0
    last_checked: float = 0
    consecutive_errors: int = 0
    total_requests: int = 0
    rate_limited_at: float = 0
    cooldown_until: float = 0
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ProviderConfig:
    PROVIDERS = {
        "openrouter": {
            "name": "OpenRouter",
            "key_prefix": "sk-or-",
            "test_url": "https://openrouter.ai/api/v1/models",
            "test_method": "GET",
            "rate_limit_rpm": 60,
            "models_endpoint": "https://openrouter.ai/api/v1/chat/completions",
        },
        "groq": {
            "name": "Groq",
            "key_prefix": "gsk_",
            "test_url": "https://api.groq.com/openai/v1/models",
            "test_method": "GET",
            "rate_limit_rpm": 30,
            "models_endpoint": "https://api.groq.com/openai/v1/chat/completions",
        },
        "gemini": {
            "name": "Google Gemini",
            "key_prefix": "AIza",
            "test_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
            "test_method": "POST",
            "rate_limit_rpm": 60,
            "models_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
        },
        "openai": {
            "name": "OpenAI",
            "key_prefix": "sk-proj-",
            "test_url": "https://api.openai.com/v1/models",
            "test_method": "GET",
            "rate_limit_rpm": 50,
            "models_endpoint": "https://api.openai.com/v1/chat/completions",
        },
    }

    @classmethod
    def get(cls, provider: str) -> Dict:
        return cls.PROVIDERS.get(provider.lower(), {})


class EncryptionManager:
    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._load_or_create_master_key()
        self.cipher = Fernet(base64.urlsafe_b64encode(
            hashlib.sha256(self.master_key).digest()
        ))

    def _load_or_create_master_key(self) -> bytes:
        key_path = "/root/.ck-nexus/master.key"
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        key = secrets.token_bytes(32)
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key)
        os.chmod(key_path, 0o600)
        return key

    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()


class UnifiedAPIKeyManager:
    def __init__(self, db_path: str = "/workspace/ck-nexus/nexus_system_sd.db"):
        self.db_path = db_path
        self.encryption = EncryptionManager()
        self.keys: Dict[str, List[APIKey]] = {}  # provider -> List[APIKey]
        self.current_index: Dict[str, int] = {}  # provider -> current key index
        self.health_check_interval = 60  # seconds
        self.max_consecutive_errors = 3
        self.cooldown_base = 60  # seconds
        self._running = False
        self._health_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._event_callbacks: List[Callable] = []

        self._init_db()
        self._load_keys()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_key_pool (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    encrypted_key TEXT NOT NULL,
                    alias TEXT,
                    status TEXT DEFAULT 'active',
                    last_used REAL DEFAULT 0,
                    last_checked REAL DEFAULT 0,
                    consecutive_errors INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    rate_limited_at REAL DEFAULT 0,
                    cooldown_until REAL DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_key_provider ON api_key_pool(provider)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_key_status ON api_key_pool(status)
            """)
            conn.commit()

    def _load_keys(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM api_key_pool").fetchall()
            for row in rows:
                key = APIKey(
                    id=row["id"],
                    provider=row["provider"],
                    encrypted_key=row["encrypted_key"],
                    alias=row["alias"] or "",
                    status=KeyStatus(row["status"]),
                    last_used=row["last_used"],
                    last_checked=row["last_checked"],
                    consecutive_errors=row["consecutive_errors"],
                    total_requests=row["total_requests"],
                    rate_limited_at=row["rate_limited_at"],
                    cooldown_until=row["cooldown_until"],
                    metadata=json.loads(row["metadata"] or "{}"),
                    created_at=row["created_at"],
                )
                if key.provider not in self.keys:
                    self.keys[key.provider] = []
                self.keys[key.provider].append(key)

    def _save_key(self, key: APIKey):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO api_key_pool 
                (id, provider, encrypted_key, alias, status, last_used, last_checked,
                 consecutive_errors, total_requests, rate_limited_at, cooldown_until,
                 metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key.id, key.provider, key.encrypted_key, key.alias, key.status.value,
                key.last_used, key.last_checked, key.consecutive_errors,
                key.total_requests, key.rate_limited_at, key.cooldown_until,
                json.dumps(key.metadata), key.created_at
            ))
            conn.commit()

    def _delete_key(self, key_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM api_key_pool WHERE id = ?", (key_id,))
            conn.commit()

    def add_key(self, provider: str, api_key: str, alias: str = "") -> str:
        provider = provider.lower()
        if provider not in ProviderConfig.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        config = ProviderConfig.get(provider)
        if not api_key.startswith(config["key_prefix"]):
            raise ValueError(f"Invalid key format for {provider}. Must start with {config['key_prefix']}")

        key_id = secrets.token_urlsafe(16)
        encrypted = self.encryption.encrypt(api_key)

        key = APIKey(
            id=key_id,
            provider=provider,
            encrypted_key=encrypted,
            alias=alias,
            status=KeyStatus.ACTIVE,
        )

        with self._lock:
            if provider not in self.keys:
                self.keys[provider] = []
                self.current_index[provider] = 0
            self.keys[provider].append(key)
            self._save_key(key)

        self._emit_event("key:added", {"provider": provider, "key_id": key_id})
        return key_id

    def remove_key(self, provider: str, key_id: str) -> bool:
        provider = provider.lower()
        with self._lock:
            if provider not in self.keys:
                return False
            for i, key in enumerate(self.keys[provider]):
                if key.id == key_id:
                    self.keys[provider].pop(i)
                    self._delete_key(key_id)
                    if self.current_index.get(provider, 0) >= len(self.keys[provider]):
                        self.current_index[provider] = 0
                    self._emit_event("key:removed", {"provider": provider, "key_id": key_id})
                    return True
        return False

    def get_key(self, provider: str) -> Optional[str]:
        provider = provider.lower()
        with self._lock:
            if provider not in self.keys or not self.keys[provider]:
                return None

            keys = self.keys[provider]
            start_idx = self.current_index.get(provider, 0)

            for i in range(len(keys)):
                idx = (start_idx + i) % len(keys)
                key = keys[idx]
                
                if key.status == KeyStatus.COOLDOWN:
                    if time.time() >= key.cooldown_until:
                        key.status = KeyStatus.ACTIVE
                        key.cooldown_until = 0
                        key.consecutive_errors = 0
                    else:
                        continue
                
                if key.status == KeyStatus.ACTIVE:
                    self.current_index[provider] = idx
                    key.last_used = time.time()
                    key.total_requests += 1
                    self._save_key(key)
                    return self.encryption.decrypt(key.encrypted_key)

            return None

    def get_keys_info(self, provider: str) -> List[Dict]:
        provider = provider.lower()
        with self._lock:
            if provider not in self.keys:
                return []
            return [
                {
                    "id": k.id[:8],
                    "alias": k.alias or f"Key-{k.id[:8]}",
                    "status": k.status.value,
                    "last_used": datetime.fromtimestamp(k.last_used).isoformat() if k.last_used else "Never",
                    "consecutive_errors": k.consecutive_errors,
                    "total_requests": k.total_requests,
                    "cooldown_remaining": max(0, int(k.cooldown_until - time.time())) if k.status == KeyStatus.COOLDOWN else 0,
                }
                for k in self.keys[provider]
            ]

    def mark_rate_limited(self, provider: str, key_id: Optional[str] = None, cooldown_seconds: Optional[int] = None):
        provider = provider.lower()
        with self._lock:
            if provider not in self.keys:
                return
            
            keys = self.keys[provider]
            if key_id:
                target_keys = [k for k in keys if k.id == key_id]
            else:
                target_keys = [keys[self.current_index.get(provider, 0)]] if keys else []

            for key in target_keys:
                if key.status == KeyStatus.ACTIVE:
                    key.consecutive_errors += 1
                    if key.consecutive_errors >= self.max_consecutive_errors:
                        key.status = KeyStatus.COOLDOWN
                        cooldown = cooldown_seconds or (self.cooldown_base * (2 ** (key.consecutive_errors - self.max_consecutive_errors)))
                        key.cooldown_until = time.time() + min(cooldown, 3600)
                        key.rate_limited_at = time.time()
                        self._emit_event("key:cooldown", {
                            "provider": provider, 
                            "key_id": key.id,
                            "duration": key.cooldown_until - time.time()
                        })
                    self._save_key(key)

    def mark_error(self, provider: str, key_id: Optional[str] = None):
        provider = provider.lower()
        with self._lock:
            if provider not in self.keys:
                return
            keys = self.keys[provider]
            target = [k for k in keys if k.id == key_id] if key_id else [keys[self.current_index.get(provider, 0)]]
            for key in target:
                key.consecutive_errors += 1
                if key.consecutive_errors >= self.max_consecutive_errors:
                    key.status = KeyStatus.COOLDOWN
                    key.cooldown_until = time.time() + self.cooldown_base
                self._save_key(key)

    def mark_success(self, provider: str, key_id: Optional[str] = None):
        provider = provider.lower()
        with self._lock:
            if provider not in self.keys:
                return
            keys = self.keys[provider]
            target = [k for k in keys if k.id == key_id] if key_id else [keys[self.current_index.get(provider, 0)]]
            for key in target:
                key.consecutive_errors = 0
                self._save_key(key)

    async def test_key(self, provider: str, key_id: str) -> Dict:
        provider = provider.lower()
        with self._lock:
            key = next((k for k in self.keys.get(provider, []) if k.id == key_id), None)
        
        if not key:
            return {"success": False, "error": "Key not found"}

        api_key = self.encryption.decrypt(key.encrypted_key)
        config = ProviderConfig.get(provider)
        
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(
                config["test_url"],
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method=config["test_method"]
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return {"success": True, "provider": provider, "key_id": key_id, "status": "valid"}
                else:
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check_all(self):
        for provider in self.keys:
            keys = self.keys[provider]
            for key in keys:
                if key.status in (KeyStatus.ACTIVE, KeyStatus.COOLDOWN):
                    result = await self.test_key(provider, key.id)
                    with self._lock:
                        if result["success"]:
                            key.status = KeyStatus.ACTIVE
                            key.consecutive_errors = 0
                            key.last_checked = time.time()
                        else:
                            key.consecutive_errors += 1
                            if key.consecutive_errors >= self.max_consecutive_errors:
                                key.status = KeyStatus.COOLDOWN
                                key.cooldown_until = time.time() + self.cooldown_base
                        key.last_checked = time.time()
                        self._save_key(key)

    def _health_loop(self):
        while self._running:
            try:
                asyncio.run(self.health_check_all())
            except Exception as e:
                print(f"[HealthCheck] Error: {e}")
            time.sleep(self.health_check_interval)

    def start(self):
        self._running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()
        print(f"[KeyManager] Started — {len(self.keys)} providers loaded")

    def stop(self):
        self._running = False
        if self._health_thread:
            self._health_thread.join(timeout=5)

    def get_pool_stats(self) -> List[Dict]:
        stats = []
        for provider, keys in self.keys.items():
            config = ProviderConfig.get(provider)
            active = sum(1 for k in keys if k.status == KeyStatus.ACTIVE)
            cooldown = sum(1 for k in keys if k.status == KeyStatus.COOLDOWN)
            error = sum(1 for k in keys if k.status == KeyStatus.ERROR)
            stats.append({
                "provider": provider,
                "name": config.get("name", provider),
                "total": len(keys),
                "active": active,
                "cooldown": cooldown,
                "error": error,
                "rate_limit_rpm": config.get("rate_limit_rpm", "N/A")
            })
        return stats

    def get_all_providers(self) -> List[Dict]:
        return [
            {
                "id": pid,
                "name": config["name"],
                "key_prefix": config["key_prefix"],
                "pool_size": len(self.keys.get(pid, [])),
                "active_keys": sum(1 for k in self.keys.get(pid, []) if k.status == KeyStatus.ACTIVE),
                "rate_limit_rpm": config["rate_limit_rpm"]
            }
            for pid, config in ProviderConfig.PROVIDERS.items()
        ]

    def on_event(self, callback: Callable):
        self._event_callbacks.append(callback)

    def _emit_event(self, event: str, data: Dict):
        for cb in self._event_callbacks:
            try:
                cb(event, data)
            except Exception:
                pass


# Global instance
_key_manager: Optional[UnifiedAPIKeyManager] = None

def get_key_manager() -> UnifiedAPIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = UnifiedAPIKeyManager()
    return _key_manager

def init_key_manager() -> UnifiedAPIKeyManager:
    global _key_manager
    _key_manager = UnifiedAPIKeyManager()
    _key_manager.start()
    return _key_manager


if __name__ == "__main__":
    # Demo
    km = init_key_manager()
    
    # Add demo keys
    try:
        km.add_key("openrouter", "sk-or-v1-REPLACED_OPENROUTER_KEY", "Primary")
        km.add_key("openrouter", "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "Backup")
        km.add_key("gemini", "GEMINI_API_KEY_REPLACED", "Gemini-Flash")
        km.add_key("openai", "sk-proj-REPLACED_OPENAI_KEY_2", "GPT-4o-mini")
    except Exception as e:
        print(f"Demo keys: {e}")
    
    print("\n=== Pool Stats ===")
    for s in km.get_pool_stats():
        print(f"  {s['name']}: {s['active']}/{s['total']} active | Rate: {s['rate_limit_rpm']} rpm")
    
    print("\n=== Keys ===")
    for provider in km.keys:
        for k in km.get_keys_info(provider):
            print(f"  {provider}: {k['alias']} ({k['status']}) - {k['total_requests']} reqs")
    
    # Test get key
    print("\n=== Test Get Key ===")
    for i in range(3):
        key = km.get_key("openrouter")
        if key:
            print(f"  Got key: {key[:20]}...")
    
    km.stop()
    print("\n✅ Demo complete")