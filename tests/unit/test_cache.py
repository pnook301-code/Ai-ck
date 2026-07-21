import pytest
from kernel.cache import CacheService, CacheBackend, MemoryBackend, NullBackend, CacheEntry


class TestCacheEntry:
    def test_not_expired_no_ttl(self):
        entry = CacheEntry("k", "v")
        assert entry.is_expired() is False

    def test_expired(self):
        import time
        entry = CacheEntry("k", "v", ttl=0.001)
        time.sleep(0.01)
        assert entry.is_expired() is True

    def test_touch(self):
        entry = CacheEntry("k", "v")
        assert entry.access_count == 0
        entry.touch()
        assert entry.access_count == 1


class TestMemoryBackend:
    def test_set_and_get(self):
        mb = MemoryBackend()
        mb.set("key", "value")
        assert mb.get("key") == "value"

    def test_get_missing(self):
        mb = MemoryBackend()
        assert mb.get("missing") is None

    def test_delete(self):
        mb = MemoryBackend()
        mb.set("key", "value")
        mb.delete("key")
        assert mb.get("key") is None

    def test_clear(self):
        mb = MemoryBackend()
        mb.set("a", 1)
        mb.set("b", 2)
        mb.clear()
        assert mb.get("a") is None
        assert mb.get("b") is None

    def test_has(self):
        mb = MemoryBackend()
        assert mb.has("key") is False
        mb.set("key", "value")
        assert mb.has("key") is True

    def test_expired_entry_returns_none(self):
        import time
        mb = MemoryBackend()
        mb.set("key", "value", ttl=0.001)
        time.sleep(0.01)
        assert mb.get("key") is None
        assert mb.has("key") is False

    def test_stats(self):
        mb = MemoryBackend()
        mb.set("a", 1)
        mb.set("b", 2)
        stats = mb.stats()
        assert stats["size"] == 2


class TestCacheService:
    def test_default_backend(self):
        cs = CacheService()
        cs.set("key", "value")
        assert cs.get("key") == "value"

    def test_null_backend(self):
        cs = CacheService(backend=CacheBackend.NULL)
        cs.set("key", "value")
        assert cs.get("key") is None

    def test_delete(self):
        cs = CacheService()
        cs.set("key", "value")
        cs.delete("key")
        assert cs.get("key") is None

    def test_clear(self):
        cs = CacheService()
        cs.set("a", 1)
        cs.set("b", 2)
        cs.clear()
        assert cs.get("a") is None

    def test_has(self):
        cs = CacheService()
        assert cs.has("key") is False
        cs.set("key", "value")
        assert cs.has("key") is True

    def test_remember_caches(self):
        cs = CacheService()
        called = 0

        def factory():
            nonlocal called
            called += 1
            return "computed"

        assert cs.remember("key", 60, factory) == "computed"
        assert cs.remember("key", 60, factory) == "computed"
        assert called == 1

    @pytest.mark.asyncio
    async def test_remember_async(self):
        cs = CacheService()
        called = 0

        async def factory():
            nonlocal called
            called += 1
            return "async_value"

        result = await cs.remember_async("key", 60, factory)
        assert result == "async_value"
        result2 = await cs.remember_async("key", 60, factory)
        assert result2 == "async_value"
        assert called == 1

    def test_remember_ttl_respected(self):
        import time
        cs = CacheService()
        called = 0

        def factory():
            nonlocal called
            called += 1
            return "fresh"

        assert cs.remember("key", 0.001, factory) == "fresh"
        time.sleep(0.01)
        assert cs.remember("key", 0.001, factory) == "fresh"
        assert called == 2

    def test_stats(self):
        cs = CacheService()
        cs.set("a", 1)
        stats = cs.stats()
        assert stats["size"] == 1

    def test_null_stats(self):
        cs = CacheService(backend=CacheBackend.NULL)
        stats = cs.stats()
        assert stats["size"] == 0


class TestNullBackend:
    def test_all_methods(self):
        nb = NullBackend()
        assert nb.get("x") is None
        nb.set("x", "v")
        nb.delete("x")
        nb.clear()
        assert nb.has("x") is False
        assert nb.stats() == {"size": 0}
