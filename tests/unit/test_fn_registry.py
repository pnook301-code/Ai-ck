import asyncio
import pytest
from kernel.fn import FunctionRegistry, FunctionDefinition, FunctionCategory, FunctionStatus, FunctionResult
from kernel.fn.category1 import SYSTEM_CORE_FUNCTIONS, register_system_core


class TestFunctionDefinition:
    def test_minimal_definition(self):
        fn = FunctionDefinition(id="1.1", name="test", description="desc", category=FunctionCategory.SYSTEM_CORE)
        assert fn.id == "1.1"
        assert fn.name == "test"
        assert fn.timeout == 30.0
        assert fn.requires_approval is False

    def test_full_definition(self):
        async def handler(input): pass
        fn = FunctionDefinition(
            id="1.5", name="Log Rotator", description="Rotate logs",
            category=FunctionCategory.SYSTEM_CORE,
            input_schema={"max_size": "string"},
            output_schema={"rotated": "integer"},
            tags=["logs", "maintenance"], timeout=60.0,
            requires_approval=True, handler=handler,
        )
        assert fn.id == "1.5"
        assert fn.handler is handler
        assert fn.requires_approval is True


class TestFunctionResult:
    def test_defaults(self):
        r = FunctionResult(function_id="1.1")
        assert r.success is False
        assert r.status == FunctionStatus.PENDING
        assert r.duration_ms == 0.0
        assert r.execution_id is not None

    def test_error_result(self):
        r = FunctionResult(function_id="1.1", success=False, error="fail", status=FunctionStatus.FAILED)
        assert r.success is False
        assert r.error == "fail"


class TestFunctionRegistry:
    @pytest.mark.asyncio
    async def test_register_and_execute(self):
        reg = FunctionRegistry()
        async def ping(input):
            return {"pong": True}
        reg.register(FunctionDefinition(id="1.1", name="ping", description="test", category=FunctionCategory.SYSTEM_CORE, handler=ping))
        result = await reg.execute("1.1")
        assert result.success is True
        assert result.output["pong"] is True

    @pytest.mark.asyncio
    async def test_register_handler(self):
        reg = FunctionRegistry()
        async def handler(input):
            return {"done": True}
        reg.register_handler("99.9", handler)
        fn = reg.get_definition("99.9")
        assert fn.id == "99.9"
        assert fn.handler is handler

    @pytest.mark.asyncio
    async def test_unknown_function(self):
        reg = FunctionRegistry()
        result = await reg.execute("nonexistent")
        assert result.success is False
        assert "Unknown function" in result.error

    @pytest.mark.asyncio
    async def test_no_handler(self):
        reg = FunctionRegistry()
        reg.register(FunctionDefinition(id="1.1", name="orphan", description="no handler", category=FunctionCategory.SYSTEM_CORE))
        result = await reg.execute("1.1")
        assert result.success is False
        assert "No handler registered" in result.error

    @pytest.mark.asyncio
    async def test_handler_error(self):
        reg = FunctionRegistry()
        async def failing(input):
            raise RuntimeError("boom")
        reg.register(FunctionDefinition(id="1.1", name="fail", description="", category=FunctionCategory.SYSTEM_CORE, handler=failing))
        result = await reg.execute("1.1")
        assert result.success is False
        assert "boom" in result.error

    @pytest.mark.asyncio
    async def test_handler_timeout(self):
        reg = FunctionRegistry()
        async def slow(input):
            await asyncio.sleep(10)
        reg.register(FunctionDefinition(id="1.1", name="slow", description="", category=FunctionCategory.SYSTEM_CORE, handler=slow, timeout=0.01))
        result = await reg.execute("1.1")
        assert result.success is False
        assert result.status == FunctionStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        reg = FunctionRegistry()
        def sync_fn(input):
            return {"sync": True}
        reg.register(FunctionDefinition(id="1.1", name="sync", description="", category=FunctionCategory.SYSTEM_CORE, handler=sync_fn))
        result = await reg.execute("1.1")
        assert result.success is True
        assert result.output["sync"] is True

    @pytest.mark.asyncio
    async def test_get_definition(self):
        reg = FunctionRegistry()
        fn = FunctionDefinition(id="1.1", name="test", description="", category=FunctionCategory.SYSTEM_CORE)
        reg.register(fn)
        assert reg.get_definition("1.1") is fn
        assert reg.get_definition("missing") is None

    @pytest.mark.asyncio
    async def test_list_functions(self):
        reg = FunctionRegistry()
        reg.register(FunctionDefinition(id="1.1", name="a", description="", category=FunctionCategory.SYSTEM_CORE))
        reg.register(FunctionDefinition(id="2.1", name="b", description="", category=FunctionCategory.INPUT_GATEWAYS))
        all_fns = reg.list_functions()
        assert len(all_fns) == 2
        core_fns = reg.list_functions(FunctionCategory.SYSTEM_CORE)
        assert len(core_fns) == 1
        assert core_fns[0].id == "1.1"

    @pytest.mark.asyncio
    async def test_find_by_name(self):
        reg = FunctionRegistry()
        reg.register(FunctionDefinition(id="4.3", name="Nuclei Scan", description="Web vuln scanner", category=FunctionCategory.SECURITY_SCANNING))
        reg.register(FunctionDefinition(id="4.4", name="SQLi Test", description="SQL injection test", category=FunctionCategory.SECURITY_SCANNING))
        results = reg.find("nuclei")
        assert len(results) == 1
        assert results[0].id == "4.3"

    @pytest.mark.asyncio
    async def test_find_by_tags(self):
        reg = FunctionRegistry()
        reg.register(FunctionDefinition(id="1.1", name="a", description="", category=FunctionCategory.SYSTEM_CORE, tags=["network", "monitoring"]))
        reg.register(FunctionDefinition(id="1.2", name="b", description="", category=FunctionCategory.SYSTEM_CORE, tags=["maintenance"]))
        results = reg.find(tags=["network"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_execute_pipeline_success(self):
        reg = FunctionRegistry()
        async def scan(input):
            return {"open_ports": [80, 443]}
        async def vuln(input):
            return {"vulnerabilities": ["CVE-2024-1234"]}
        reg.register(FunctionDefinition(id="4.1", name="scan", description="", category=FunctionCategory.SECURITY_SCANNING, handler=scan))
        reg.register(FunctionDefinition(id="4.3", name="vuln", description="", category=FunctionCategory.SECURITY_SCANNING, handler=vuln))
        result = await reg.execute_pipeline([
            {"fn": "4.1", "params": {"target": "example.com"}},
            {"fn": "4.3", "params": {"url": "https://example.com"}},
        ])
        assert result["results"]["4.1"]["success"] is True
        assert result["results"]["4.3"]["success"] is True
        assert result["results"]["4.1"]["output"]["open_ports"] == [80, 443]

    @pytest.mark.asyncio
    async def test_execute_pipeline_stop_on_success(self):
        reg = FunctionRegistry()
        async def fn_a(input): return {"step": "a"}
        async def fn_b(input): return {"step": "b"}
        reg.register(FunctionDefinition(id="a", name="a", description="", category=FunctionCategory.SYSTEM_CORE, handler=fn_a))
        reg.register(FunctionDefinition(id="b", name="b", description="", category=FunctionCategory.SYSTEM_CORE, handler=fn_b))
        result = await reg.execute_pipeline([
            {"fn": "a", "params": {}, "on_success": "stop"},
            {"fn": "b", "params": {}},
        ])
        assert result["results"]["a"]["success"] is True
        assert "b" not in result["results"]

    @pytest.mark.asyncio
    async def test_execute_pipeline_condition_skip(self):
        reg = FunctionRegistry()
        async def fn_a(input): return {"ports": []}
        async def fn_b(input): return {"scanned": True}
        reg.register(FunctionDefinition(id="a", name="a", description="", category=FunctionCategory.SYSTEM_CORE, handler=fn_a))
        reg.register(FunctionDefinition(id="b", name="b", description="", category=FunctionCategory.SYSTEM_CORE, handler=fn_b))
        result = await reg.execute_pipeline([
            {"fn": "a", "params": {}},
            {"fn": "b", "params": {}, "condition": "a.ports"},
        ])
        assert result["results"]["b"]["success"] is True

    @pytest.mark.asyncio
    async def test_functions_property(self):
        reg = FunctionRegistry()
        reg.register(FunctionDefinition(id="1.1", name="t", description="", category=FunctionCategory.SYSTEM_CORE))
        assert "1.1" in reg.functions

    @pytest.mark.asyncio
    async def test_get_stats(self):
        reg = FunctionRegistry()
        async def ok(input): return {}
        reg.register(FunctionDefinition(id="1.1", name="t", description="", category=FunctionCategory.SYSTEM_CORE, handler=ok))
        stats = reg.get_stats()
        assert stats["registered"] == 1
        assert stats["executions"] == 0
        await reg.execute("1.1")
        stats = reg.get_stats()
        assert stats["executions"] == 1
        assert stats["successful"] == 1

    @pytest.mark.asyncio
    async def test_get_history(self):
        reg = FunctionRegistry()
        async def ok(input): return {}
        reg.register(FunctionDefinition(id="1.1", name="t", description="", category=FunctionCategory.SYSTEM_CORE, handler=ok))
        await reg.execute("1.1")
        history = reg.get_history()
        assert len(history) == 1
        assert history[0].function_id == "1.1"


class TestSystemCoreRegistration:
    @pytest.mark.asyncio
    async def test_all_10_functions_registered(self):
        reg = FunctionRegistry()
        register_system_core(reg)
        fns = reg.list_functions(FunctionCategory.SYSTEM_CORE)
        assert len(fns) == 10
        ids = sorted([f.id for f in fns], key=lambda x: tuple(int(n) for n in x.split(".")))
        assert ids == [f"1.{i}" for i in range(1, 11)]

    @pytest.mark.asyncio
    async def test_each_function_executes_successfully(self):
        reg = FunctionRegistry()
        register_system_core(reg)
        for i in range(1, 11):
            fn_id = f"1.{i}"
            result = await reg.execute(fn_id)
            assert result.success is True, f"{fn_id} failed: {result.error}"
            assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_function_with_custom_input(self):
        reg = FunctionRegistry()
        register_system_core(reg)
        result = await reg.execute("1.4", {"threshold": 95})
        assert result.success is True
        assert result.output["threshold"] == 95

    @pytest.mark.asyncio
    async def test_all_have_tags(self):
        reg = FunctionRegistry()
        register_system_core(reg)
        for fn in reg.list_functions(FunctionCategory.SYSTEM_CORE):
            assert len(fn.tags) > 0, f"{fn.id} has no tags"

    @pytest.mark.asyncio
    async def test_all_have_input_schema(self):
        reg = FunctionRegistry()
        register_system_core(reg)
        for fn in reg.list_functions(FunctionCategory.SYSTEM_CORE):
            assert isinstance(fn.input_schema, dict)

    @pytest.mark.asyncio
    async def test_all_have_output_schema(self):
        reg = FunctionRegistry()
        register_system_core(reg)
        for fn in reg.list_functions(FunctionCategory.SYSTEM_CORE):
            assert isinstance(fn.output_schema, dict)
