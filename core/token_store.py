"""Encrypted Token Storage - AES-256 Fernet encryption"""
import os
import json
from datetime import datetime

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class TokenStore:
    def __init__(self, store_dir=None):
        self.store_dir = store_dir or os.path.expanduser("~/.ck-nexus/credentials")
        os.makedirs(self.store_dir, exist_ok=True)
        self.key_file = os.path.join(self.store_dir, ".master_key")
        self.token_file = os.path.join(self.store_dir, "tokens.enc")
        self._fernet = self._init_fernet()

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

    def save_tokens(self, provider, tokens):
        all_tokens = self.load_all()
        all_tokens[provider] = {
            "data": self._encrypt(tokens),
            "updated_at": datetime.now().isoformat()
        }
        with open(self.token_file, "w") as f:
            json.dump(all_tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)

    def load_tokens(self, provider):
        all_tokens = self.load_all()
        entry = all_tokens.get(provider)
        if not entry:
            return None
        return self._decrypt(entry.get("data", ""))

    def load_all(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def delete_tokens(self, provider):
        all_tokens = self.load_all()
        if provider in all_tokens:
            del all_tokens[provider]
            with open(self.token_file, "w") as f:
                json.dump(all_tokens, f, indent=2)
            return True
        return False

    def delete_all(self):
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        return True

    def has_tokens(self, provider):
        return self.load_tokens(provider) is not None

    def list_providers(self):
        return list(self.load_all().keys())

    def get_status(self):
        providers = self.list_providers()
        return {
            "encrypted": HAS_CRYPTO,
            "providers": providers,
            "count": len(providers),
            "store": self.token_file
        }
