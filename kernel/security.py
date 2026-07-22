"""Security Service - authentication and authorization"""
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import time
import uuid


class AuthProvider(Enum):
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    BASIC = "basic"


@dataclass
class AuthorizationPolicy:
    name: str
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)
    deny: bool = False


@dataclass
class UserPrincipal:
    id: str
    username: str
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    authenticated: bool = False
    token: Optional[str] = None


@dataclass
class TokenEntry:
    principal: UserPrincipal
    created_at: float
    ttl: int


class SecurityService:
    def __init__(self, logger: Any = None):
        self._providers: Dict[AuthProvider, Any] = {}
        self._policies: Dict[str, AuthorizationPolicy] = {}
        self._api_keys: Dict[str, tuple[UserPrincipal, float]] = {}
        self._secret_key: str = str(uuid.uuid4())
        self._tokens: Dict[str, TokenEntry] = {}
        self._logger = logger
        self._bcrypt_available = False
        try:
            import bcrypt as _bc
            self._bc = _bc
            self._bcrypt_available = True
        except ImportError:
            pass

    def configure(self, provider: AuthProvider, config: Dict[str, Any] = None):
        self._providers[provider] = config or {}

    def add_policy(self, policy: AuthorizationPolicy):
        self._policies[policy.name] = policy

    def add_api_key(self, key: str, principal: UserPrincipal):
        self._api_keys[key] = (principal, time.time())

    def generate_api_key(self, principal: UserPrincipal) -> str:
        key = f"ck_{uuid.uuid4().hex}"
        self._api_keys[key] = (principal, time.time())
        return key

    def revoke_api_key(self, key: str):
        self._api_keys.pop(key, None)

    def authenticate(self, token: str, provider: AuthProvider = None) -> Optional[UserPrincipal]:
        if provider == AuthProvider.API_KEY or provider is None:
            entry = self._api_keys.get(token)
            if entry:
                principal, _ = entry
                principal.authenticated = True
                principal.token = token
                return principal

        if provider == AuthProvider.JWT or provider is None:
            entry = self._tokens.get(token)
            if entry:
                if time.time() - entry.created_at > entry.ttl:
                    self._tokens.pop(token, None)
                    return None
                entry.principal.authenticated = True
                entry.principal.token = token
                return entry.principal

        return None

    def create_token(self, principal: UserPrincipal, ttl: int = 3600) -> str:
        token = f"ckt_{uuid.uuid4().hex}"
        self._tokens[token] = TokenEntry(principal=principal, created_at=time.time(), ttl=ttl)
        return token

    def revoke_token(self, token: str):
        self._tokens.pop(token, None)

    def authorize(self, principal: UserPrincipal, policy_name: str) -> bool:
        policy = self._policies.get(policy_name)
        if not policy:
            return True

        if policy.deny:
            return False

        if policy.roles and not principal.roles.intersection(policy.roles):
            return False

        if policy.permissions and not principal.permissions.intersection(policy.permissions):
            return False

        return True

    def authorize_all(self, principal: UserPrincipal, policy_names: List[str]) -> Dict[str, bool]:
        return {name: self.authorize(principal, name) for name in policy_names}

    def hash_password(self, password: str) -> str:
        if self._bcrypt_available:
            return self._bc.hashpw(password.encode(), self._bc.gensalt()).decode()
        salt = uuid.uuid4().hex
        return f"sha256:{salt}:{hashlib.sha256((salt + password).encode()).hexdigest()}"

    def verify_password(self, password: str, hashed: str) -> bool:
        if hashed.startswith("$2"):
            try:
                return self._bc.checkpw(password.encode(), hashed.encode())
            except Exception:
                return False
        if hashed.startswith("sha256:"):
            _, salt, hash_value = hashed.split(":", 2)
            return hash_value == hashlib.sha256((salt + password).encode()).hexdigest()
        salt, hash_value = hashed.split(":", 1)
        return hash_value == hashlib.sha256((salt + password).encode()).hexdigest()

    def sign(self, data: str) -> str:
        return hmac.new(
            self._secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, data: str, signature: str) -> bool:
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)
