import pytest
from kernel.bootstrap import BootstrapService, BootstrapPhase


class TestBootstrapPhase:
    def test_defaults(self):
        bp = BootstrapPhase(name="init", order=1)
        assert bp.required is True
        assert bp.timeout == 30.0
        assert bp.success is False

    def test_with_values(self):
        bp = BootstrapPhase(name="test", order=5, required=False, timeout=10.0)
        assert bp.required is False
        assert bp.timeout == 10.0


class TestBootstrapService:
    @pytest.mark.asyncio
    async def test_add_phase(self):
        bs = BootstrapService()
        bs.add_phase("init", order=1)
        results = bs.get_results()
        assert "init" in results

    @pytest.mark.asyncio
    async def test_duplicate_phase_ignored(self):
        bs = BootstrapService()
        bs.add_phase("init", order=1)
        bs.add_phase("init", order=2)
        assert len(bs._phases) == 1

    @pytest.mark.asyncio
    async def test_add_handler(self):
        bs = BootstrapService()
        bs.add_phase("init", order=1)

        async def handler():
            pass

        bs.add_handler("init", handler)
        assert len(bs._phases["init"].handlers) == 1

    @pytest.mark.asyncio
    async def test_handler_to_nonexistent_phase(self):
        bs = BootstrapService()
        bs.add_handler("missing", lambda: None)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        bs = BootstrapService()
        bs.add_phase("init", order=1)
        bs.add_phase("start", order=2)
        order = []

        async def h1():
            order.append(1)

        async def h2():
            order.append(2)

        bs.add_handler("init", h1)
        bs.add_handler("start", h2)
        success = await bs.execute()
        assert success is True
        assert order == [1, 2]

    @pytest.mark.asyncio
    async def test_empty_phase_skipped(self):
        bs = BootstrapService()
        bs.add_phase("empty", order=1)
        success = await bs.execute()
        assert success is True

    @pytest.mark.asyncio
    async def test_required_phase_fails(self):
        bs = BootstrapService()
        bs.add_phase("critical", order=1)

        async def fail():
            raise RuntimeError("boom")

        bs.add_handler("critical", fail)
        success = await bs.execute()
        assert success is False

    @pytest.mark.asyncio
    async def test_non_required_phase_fails_continues(self):
        bs = BootstrapService()
        bs.add_phase("optional", order=1, required=False)
        bs.add_phase("main", order=2)

        async def fail():
            raise RuntimeError("fail")

        async def ok():
            pass

        bs.add_handler("optional", fail)
        bs.add_handler("main", ok)
        success = await bs.execute()
        assert success is True

    @pytest.mark.asyncio
    async def test_phase_timeout(self):
        bs = BootstrapService()
        bs.add_phase("slow", order=1, timeout=0.01)

        async def hang():
            await asyncio.sleep(10)

        bs.add_handler("slow", hang)
        success = await bs.execute()
        assert success is False

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        bs = BootstrapService()
        bs.add_phase("sync", order=1)
        executed = []

        def handler():
            executed.append("done")

        bs.add_handler("sync", handler)
        success = await bs.execute()
        assert success is True
        assert executed == ["done"]

    @pytest.mark.asyncio
    async def test_multiple_handlers_in_phase(self):
        bs = BootstrapService()
        bs.add_phase("multi", order=1)
        results = []

        async def a():
            results.append("a")

        async def b():
            results.append("b")

        bs.add_handler("multi", a)
        bs.add_handler("multi", b)
        await bs.execute()
        assert sorted(results) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_get_results(self):
        bs = BootstrapService()
        bs.add_phase("init", order=1)

        async def ok():
            pass

        bs.add_handler("init", ok)
        await bs.execute()
        results = bs.get_results()
        assert results["init"]["success"] is True
        assert results["init"]["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_is_healthy_before_execute(self):
        bs = BootstrapService()
        assert bs.is_healthy() is False

    @pytest.mark.asyncio
    async def test_is_healthy_after_success(self):
        bs = BootstrapService()
        bs.add_phase("init", order=1)

        async def ok():
            pass

        bs.add_handler("init", ok)
        await bs.execute()
        assert bs.is_healthy() is True

    @pytest.mark.asyncio
    async def test_is_healthy_after_failure(self):
        bs = BootstrapService()
        bs.add_phase("req", order=1)

        async def fail():
            raise RuntimeError("fail")

        bs.add_handler("req", fail)
        await bs.execute()
        assert bs.is_healthy() is False

    @pytest.mark.asyncio
    async def test_exception_in_handler(self):
        bs = BootstrapService()

        async def fail():
            raise ValueError("custom error")

        bs.add_phase("test", order=1)
        bs.add_handler("test", fail)
        success = await bs.execute()
        assert success is False
        assert "custom error" in bs._phases["test"].error
