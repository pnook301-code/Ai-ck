import pytest
from kernel.health import HealthChecker, HealthCheck, HealthStatus


class TestHealthCheck:
    def test_default_status(self):
        hc = HealthCheck(name="test")
        assert hc.status == HealthStatus.UNKNOWN

    def test_with_status(self):
        hc = HealthCheck(name="test", status=HealthStatus.HEALTHY, message="ok")
        assert hc.status == HealthStatus.HEALTHY
        assert hc.message == "ok"


class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_register_and_run(self):
        checker = HealthChecker()

        async def check_db():
            return HealthCheck(name="db", status=HealthStatus.HEALTHY, message="connected")

        checker.register("db", check_db)
        results = await checker.run_checks()
        assert results["db"].status == HealthStatus.HEALTHY
        assert results["db"].message == "connected"

    @pytest.mark.asyncio
    async def test_run_single_check(self):
        checker = HealthChecker()

        async def check():
            return HealthCheck(name="x", status=HealthStatus.HEALTHY)

        checker.register("x", check)
        result = await checker.run_check("x")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_run_check_no_handler(self):
        checker = HealthChecker()
        result = await checker.run_check("missing")
        assert result.status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_handler_returns_bool(self):
        checker = HealthChecker()

        async def check():
            return True

        checker.register("ok", check)
        result = await checker.run_check("ok")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_handler_returns_false(self):
        checker = HealthChecker()

        async def check():
            return False

        checker.register("fail", check)
        result = await checker.run_check("fail")
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_handler_exception(self):
        checker = HealthChecker()

        async def check():
            raise ConnectionError("db down")

        checker.register("db", check)
        result = await checker.run_check("db")
        assert result.status == HealthStatus.UNHEALTHY
        assert "db down" in result.message

    @pytest.mark.asyncio
    async def test_handler_timeout(self):
        checker = HealthChecker()

        async def slow():
            await asyncio.sleep(20)
            return HealthCheck(name="slow", status=HealthStatus.HEALTHY)

        checker.register("slow", slow)
        result = await checker.run_check("slow")
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_unregister(self):
        checker = HealthChecker()

        async def check():
            return HealthCheck(name="x", status=HealthStatus.HEALTHY)

        checker.register("x", check)
        checker.unregister("x")
        result = await checker.run_check("x")
        assert result.status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_status_single(self):
        checker = HealthChecker()

        async def check():
            return HealthCheck(name="x", status=HealthStatus.HEALTHY)

        checker.register("x", check)
        await checker.run_checks()
        assert checker.get_status("x") == HealthStatus.HEALTHY
        assert checker.get_status("missing") == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_status_overall_healthy(self):
        checker = HealthChecker()

        async def ok():
            return HealthCheck(name="a", status=HealthStatus.HEALTHY)

        async def ok2():
            return HealthCheck(name="b", status=HealthStatus.HEALTHY)

        checker.register("a", ok)
        checker.register("b", ok2)
        await checker.run_checks()
        assert checker.get_status() == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_status_overall_unhealthy(self):
        checker = HealthChecker()

        async def ok():
            return HealthCheck(name="a", status=HealthStatus.HEALTHY)

        async def fail():
            return HealthCheck(name="b", status=HealthStatus.UNHEALTHY)

        checker.register("a", ok)
        checker.register("b", fail)
        await checker.run_checks()
        assert checker.get_status() == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_get_status_overall_degraded(self):
        checker = HealthChecker()

        async def ok():
            return HealthCheck(name="a", status=HealthStatus.HEALTHY)

        async def deg():
            return HealthCheck(name="b", status=HealthStatus.DEGRADED)

        checker.register("a", ok)
        checker.register("b", deg)
        await checker.run_checks()
        assert checker.get_status() == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_get_status_no_results(self):
        checker = HealthChecker()
        assert checker.get_status() == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_results(self):
        checker = HealthChecker()

        async def ok():
            return HealthCheck(name="a", status=HealthStatus.HEALTHY)

        checker.register("a", ok)
        await checker.run_checks()
        results = checker.get_results()
        assert "a" in results

    @pytest.mark.asyncio
    async def test_summary(self):
        checker = HealthChecker()

        async def ok():
            return HealthCheck(name="a", status=HealthStatus.HEALTHY)

        checker.register("a", ok)
        await checker.run_checks()
        summary = checker.summary()
        assert summary["overall"] == "healthy"
        assert summary["total"] == 1
        assert summary["healthy"] == 1
