import pytest
from kernel.state import StateManager, StateSnapshot


class TestStateManager:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        sm = StateManager()
        sm.set("key", "value")
        assert sm.get("key") == "value"

    @pytest.mark.asyncio
    async def test_get_default(self):
        sm = StateManager()
        assert sm.get("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_delete(self):
        sm = StateManager()
        sm.set("key", "value")
        sm.delete("key")
        assert sm.get("key") is None

    @pytest.mark.asyncio
    async def test_update(self):
        sm = StateManager()
        sm.update({"a": 1, "b": 2})
        assert sm.get("a") == 1
        assert sm.get("b") == 2

    @pytest.mark.asyncio
    async def test_clear(self):
        sm = StateManager()
        sm.set("a", 1)
        sm.set("b", 2)
        sm.clear()
        assert len(sm.all()) == 0

    @pytest.mark.asyncio
    async def test_snapshot(self):
        sm = StateManager()
        sm.set("key", "value")
        snap = sm.snapshot()
        assert isinstance(snap, StateSnapshot)
        assert snap.data["key"] == "value"
        assert snap.version >= 1

    @pytest.mark.asyncio
    async def test_persist_and_load(self, temp_dir):
        sm = StateManager(data_dir=temp_dir)
        sm.set("persistent", "data")
        await sm.persist()
        sm2 = StateManager(data_dir=temp_dir)
        await sm2._load()
        assert sm2.get("persistent") == "data"

    @pytest.mark.asyncio
    async def test_persist_only_when_dirty(self, temp_dir):
        sm = StateManager(data_dir=temp_dir)
        await sm.persist()
        import os
        assert os.path.exists(sm._state_file) is False

    @pytest.mark.asyncio
    async def test_start_stop(self, temp_dir):
        sm = StateManager(data_dir=temp_dir)
        await sm.start()
        sm.set("x", 1)
        await sm.stop()

    @pytest.mark.asyncio
    async def test_close(self, temp_dir):
        sm = StateManager(data_dir=temp_dir)
        sm.set("x", 1)
        await sm.close()

    @pytest.mark.asyncio
    async def test_all(self):
        sm = StateManager()
        sm.set("a", 1)
        sm.set("b", 2)
        data = sm.all()
        assert data == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_version_increments_on_persist(self, temp_dir):
        sm = StateManager(data_dir=temp_dir)
        sm.set("x", 1)
        await sm.persist()
        v1 = sm.snapshot().version
        sm.set("y", 2)
        await sm.persist()
        v2 = sm.snapshot().version
        assert v2 > v1


class TestStateSnapshot:
    def test_defaults(self):
        snap = StateSnapshot()
        assert snap.data == {}
        assert snap.version == 1

    def test_with_data(self):
        snap = StateSnapshot(data={"key": "val"}, version=5)
        assert snap.data["key"] == "val"
        assert snap.version == 5
