"""Tests for OrchestratorEngine — integrates Kernel + Agents + Functions + Memory"""

import pytest
from kernel.orchestrator import OrchestratorEngine


@pytest.fixture
def engine():
    eng = OrchestratorEngine()
    eng.bootstrap()
    return eng


class TestOrchestratorEngine:
    @pytest.mark.asyncio
    async def test_bootstrap_registers_functions(self, engine):
        assert len(engine.fn_registry._functions) == 120

    @pytest.mark.asyncio
    async def test_process_stores_memory(self, engine):
        await engine.process("hello world")
        units = engine.memory.recall("hello")
        assert len(units) >= 1
        assert "hello" in units[0].content

    @pytest.mark.asyncio
    async def test_process_returns_plan_and_results(self, engine):
        result = await engine.process("implement a feature")
        assert "input" in result
        assert "plan" in result
        assert "results" in result
        assert "memory" in result

    @pytest.mark.asyncio
    async def test_process_multiple_queries(self, engine):
        await engine.process("first query")
        await engine.process("second query")
        await engine.process("third query")
        assert engine.memory.stats.total_units >= 3

    @pytest.mark.asyncio
    async def test_get_status(self, engine):
        status = engine.get_status()
        assert "memory" in status
        assert "functions" in status
        assert "agents" in status
        assert status["functions"]["registered"] == 120

    @pytest.mark.asyncio
    async def test_remember_event(self, engine):
        await engine.event_bus.emit("memory.remember", {"content": "event memory", "tags": ["event"]})
        await engine.process("find event memory")
        assert engine.memory.stats.total_units >= 2

    @pytest.mark.asyncio
    async def test_fn_execute_via_engine(self, engine):
        result = await engine.fn_registry.execute("1.1", {"force": True})
        assert result.success
        assert result.output["force"] is True

    @pytest.mark.asyncio
    async def test_full_workflow(self, engine):
        result = await engine.process("scan example.com for vulnerabilities")
        assert result["plan"]["objective"] == "scan example.com for vulnerabilities"
        assert len(result["results"]) > 0


class TestOrchestratorEvents:
    @pytest.mark.asyncio
    async def test_event_bus_integration(self, engine):
        events = []

        async def handler(event):
            events.append(event.name)

        engine.event_bus.on("orchestrator.cycle.complete", handler)
        await engine.process("test event")
        assert "orchestrator.cycle.complete" in events

    @pytest.mark.asyncio
    async def test_multiple_event_types(self, engine):
        engine.memory.remember("test data")
        results = engine.memory.recall("test")
        assert len(results) >= 1


class TestOrchestratorVideoWatch:
    @pytest.mark.asyncio
    async def test_watch_not_detected(self, engine):
        result = await engine.process("hello world")
        assert "video" not in result

    @pytest.mark.asyncio
    async def test_watch_plugin_parse(self, engine):
        params = engine.watch_plugin.parse("/watch https://example.com/v.mp4 What is this?")
        assert params is not None
        assert params["source"] == "https://example.com/v.mp4"

    @pytest.mark.asyncio
    async def test_watch_plugin_returns_none_for_normal(self, engine):
        assert engine.watch_plugin.parse("just a normal message") is None
