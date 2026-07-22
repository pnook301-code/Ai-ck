import pytest
from kernel.fn import FunctionRegistry, FunctionCategory, register_all_categories


@pytest.fixture
def registry():
    reg = FunctionRegistry()
    register_all_categories(reg)
    return reg


class TestRegistration:
    def test_registers_all_110(self, registry):
        assert len(registry._functions) == 110

    def test_categories_have_10_each(self, registry):
        for cat in FunctionCategory:
            fns = registry.list_functions(cat)
            assert len(fns) == 10, f"{cat.value} has {len(fns)} functions"

    def test_all_have_handlers(self, registry):
        for fn_id, fn_def in registry._functions.items():
            assert fn_def.handler is not None, f"{fn_id} has no handler"


class TestExecution:
    @pytest.mark.asyncio
    async def test_all_execute_successfully(self, registry):
        for fn_id in registry._functions:
            r = await registry.execute(fn_id, {"test": True})
            assert r.success, f"{fn_id} failed: {r.error}"
            assert r.status.value == "success"

    @pytest.mark.asyncio
    async def test_system_core_all(self, registry):
        for fn_id in [f"1.{n}" for n in range(1, 11)]:
            r = await registry.execute(fn_id, {"tool": "curl"})
            assert r.success and r.output is not None

    @pytest.mark.asyncio
    async def test_input_gateways_all(self, registry):
        r = await registry.execute("2.1", {"url": "https://example.com"})
        assert r.success and r.output["url"] == "https://example.com"
        r = await registry.execute("2.5", {"urls": ["a.com", "b.com"]})
        assert r.success and len(r.output["urls"]) == 2

    @pytest.mark.asyncio
    async def test_osint_all(self, registry):
        r = await registry.execute("3.1", {"target": "example.com"})
        assert r.success
        r = await registry.execute("3.9", {"ip": "8.8.8.8"})
        assert r.success and r.output["ip"] == "8.8.8.8"

    @pytest.mark.asyncio
    async def test_security_scanning_all(self, registry):
        r = await registry.execute("4.1", {"target": "10.0.0.1"})
        assert r.success and 22 in r.output["open_ports"]
        r = await registry.execute("4.7", {"url": "https://example.com"})
        assert "missing_headers" in r.output

    @pytest.mark.asyncio
    async def test_offensive_all(self, registry):
        r = await registry.execute("5.1", {"target": "10.0.0.1", "cve": "CVE-2024-1234"})
        assert r.success and r.output["cve"] == "CVE-2024-1234"
        r = await registry.execute("5.10", {"lhost": "10.0.0.5"})
        assert r.success

    @pytest.mark.asyncio
    async def test_storage_all(self, registry):
        r = await registry.execute("6.1", {"collection": "scans", "data": {}})
        assert r.success and r.output["stored"]
        r = await registry.execute("6.10", {"timeframe": "7d"})
        assert r.output["timeframe"] == "7d"

    @pytest.mark.asyncio
    async def test_ai_mcp_all(self, registry):
        r = await registry.execute("7.1", {"prompt": "Hello"})
        assert r.success
        r = await registry.execute("7.9", {"query": "security"})
        assert r.output["query"] == "security"

    @pytest.mark.asyncio
    async def test_network_proxy_all(self, registry):
        r = await registry.execute("8.1", {})
        assert r.success
        r = await registry.execute("8.7", {"url": "https://example.com"})
        assert r.output["status"] == 200

    @pytest.mark.asyncio
    async def test_termux_mobile_all(self, registry):
        r = await registry.execute("9.1", {"command": "whoami"})
        assert r.success and r.output["exit_code"] == 0
        r = await registry.execute("9.9", {})
        assert len(r.output["networks"]) > 0

    @pytest.mark.asyncio
    async def test_advanced_logic_all(self, registry):
        r = await registry.execute("10.1", {"condition": "true", "if_true": ["1.1"]})
        assert r.success
        r = await registry.execute("10.10", {"steps": [{"fn": "1.1", "params": {}}]})
        assert r.output["status"] == "ready"

    @pytest.mark.asyncio
    async def test_nonexistent_function(self, registry):
        r = await registry.execute("99.99", {})
        assert not r.success
        assert "Unknown" in r.error


class TestFind:
    def test_find_by_query(self, registry):
        results = registry.find("port")
        assert len(results) >= 3

    def test_find_by_id(self, registry):
        results = registry.find("2.1")
        assert len(results) >= 1

    def test_find_empty(self, registry):
        results = registry.find("xyznonexistent12345")
        assert len(results) == 0

    def test_find_case_insensitive(self, registry):
        results = registry.find("DNS")
        assert len(results) >= 1

    def test_find_tags(self, registry):
        results = registry.find(tags=["config"])
        assert len(results) >= 1

    def test_list_by_category(self, registry):
        system = registry.list_functions(FunctionCategory.SYSTEM_CORE)
        network = registry.list_functions(FunctionCategory.NETWORK_PROXY)
        assert all(f.category == FunctionCategory.SYSTEM_CORE for f in system)
        assert all(f.category == FunctionCategory.NETWORK_PROXY for f in network)


class TestPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_simple(self, registry):
        steps = [
            {"fn": "1.1", "params": {"force": True}},
            {"fn": "1.2", "params": {"service": "db"}},
        ]
        result = await registry.execute_pipeline(steps)
        assert "results" in result
        assert result["results"]["1.1"]["success"]
        assert result["results"]["1.2"]["success"]

    @pytest.mark.asyncio
    async def test_pipeline_skip_on_condition(self, registry):
        steps = [
            {"fn": "1.1", "params": {}},
            {"fn": "1.2", "params": {}, "condition": "False"},
        ]
        result = await registry.execute_pipeline(steps)
        assert result["results"]["1.2"]["success"]

    @pytest.mark.asyncio
    async def test_pipeline_chain_multiple_categories(self, registry):
        steps = [
            {"fn": "2.1", "params": {"url": "https://example.com"}},
            {"fn": "4.7", "params": {"url": "https://example.com"}},
            {"fn": "6.1", "params": {"collection": "results", "data": {}}},
        ]
        result = await registry.execute_pipeline(steps)
        assert all(v["success"] for v in result["results"].values())


class TestStats:
    @pytest.mark.asyncio
    async def test_stats_tracking(self, registry):
        stats = registry.get_stats()
        assert stats["registered"] == 110
        assert stats["executions"] == 0

        await registry.execute("1.1", {})
        await registry.execute("1.2", {})

        stats = registry.get_stats()
        assert stats["executions"] == 2
        assert stats["successful"] == 2

    @pytest.mark.asyncio
    async def test_history(self, registry):
        await registry.execute("1.1", {"test": True})
        await registry.execute("2.1", {"url": "x"})
        history = registry.get_history()
        assert len(history) == 2
        assert history[0].function_id == "1.1"
