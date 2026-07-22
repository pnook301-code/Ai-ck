"""Cache Service - multiple backend support"""
from typing import Any, Dict, Optional, Callable
from enum import Enum
import time
import threading


class CacheBackend(Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    NULL = "null"


class CacheEntry:
    def __init__(self, key: str, value: Any, ttl: float = None):
        self.key = key
        self.value = value
        self.created = time.time()
        self.ttl = ttl
        self.access_count = 0

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() - self.created > self.ttl

    def touch(self):
        self.access_count += 1


class MemoryBackend:
    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                return None
            entry.touch()
            return entry.value

    def set(self, key: str, value: Any, ttl: float = None):
        with self._lock:
            self._store[key] = CacheEntry(key, value, ttl)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def has(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._store[key]
                return False
            return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._store),
                "entries": len(self._store),
            }


class CacheService:
    """Multi-backend cache service"""

    def __init__(self, backend: CacheBackend = CacheBackend.MEMORY, logger: Any = None, **options):
        self._backend_type = backend
        self._options = options
        self._logger = logger
        self._backend = self._create_backend(backend, options)

    def _create_backend(self, backend: CacheBackend, options: Dict) -> Any:
        if backend == CacheBackend.MEMORY:
            return MemoryBackend()
        elif backend == CacheBackend.NULL:
            return NullBackend()
        elif backend == CacheBackend.REDIS:
            from .cache_redis import RedisBackend
            return RedisBackend(**options)
        elif backend == CacheBackend.DISK:
            from .cache_disk import DiskBackend
            return DiskBackend(**options)
        return MemoryBackend()

    def get(self, key: str) -> Optional[Any]:
        try:
            return self._backend.get(key)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: float = None):
        try:
            self._backend.set(key, value, ttl)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Cache set error: {e}")

    def remember(self, key: str, ttl: float, factory: Callable) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl)
        return value

    async def remember_async(self, key: str, ttl: float, factory: Callable) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        import asyncio
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        self.set(key, value, ttl)
        return value

    def delete(self, key: str):
        try:
            self._backend.delete(key)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Cache delete error: {e}")

    def clear(self):
        try:
            self._backend.clear()
        except Exception as e:
            if self._logger:
                self._logger.error(f"Cache clear error: {e}")

    def has(self, key: str) -> bool:
        try:
            return self._backend.has(key)
        except Exception:
            return False

    def stats(self) -> Dict[str, Any]:
        try:
            return self._backend.stats()
        except Exception:
            return {"error": "unavailable"}


class NullBackend:
    def get(self, key): return None
    def set(self, key, value, ttl=None): pass
    def delete(self, key): pass
    def clear(self): pass
    def has(self, key): return False
    def stats(self): return {"size": 0}
