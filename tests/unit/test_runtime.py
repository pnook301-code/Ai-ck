import pytest
from kernel.runtime import KernelRuntime, KernelState
from kernel.config import KernelConfig


class TestKernelState:
    def test_enum_values(self):
        assert KernelState.STOPPED.value == "stopped"
        assert KernelState.STARTING.value == "starting"
        assert KernelState.RUNNING.value == "running"
        assert KernelState.STOPPING.value == "stopping"
        assert KernelState.ERROR.value == "error"


class TestKernelRuntime:
    @pytest.mark.asyncio
    async def test_start_initializes_services(self):
        config = KernelConfig(name="test-kernel")
        kernel = KernelRuntime(config=config)
        assert kernel.state == KernelState.STOPPED

        success = await kernel.start()
        assert success is True
        assert kernel.state == KernelState.RUNNING
        assert kernel.registry is not None
        assert kernel.event_bus is not None
        assert kernel.command_bus is not None
        assert kernel.state_manager is not None
        assert kernel.metrics is not None
        assert kernel.health_checker is not None
        assert kernel.container is not None
        assert kernel.start_time > 0

        await kernel.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_started(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()
        success = await kernel.start()
        assert success is False
        await kernel.stop()

    @pytest.mark.asyncio
    async def test_stop_returns_false_when_not_running(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        success = await kernel.stop()
        assert success is False

    @pytest.mark.asyncio
    async def test_stop_gracefully(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()

        shutdown_called = False

        async def on_shutdown():
            nonlocal shutdown_called
            shutdown_called = True

        kernel.on_shutdown(on_shutdown)
        success = await kernel.stop()
        assert success is True
        assert kernel.state == KernelState.STOPPED
        assert shutdown_called is True

    @pytest.mark.asyncio
    async def test_get_uptime(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        assert kernel.get_uptime() == 0
        await kernel.start()
        uptime = kernel.get_uptime()
        assert uptime > 0
        await kernel.stop()

    @pytest.mark.asyncio
    async def test_get_status(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()
        status = kernel.get_status()
        assert status["state"] == "running"
        assert status["uptime_seconds"] > 0
        assert status["background_tasks"] == 3
        assert status["registered_services"] == 8
        await kernel.stop()

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_executed(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()

        call_order = []

        async def cb1():
            call_order.append(1)

        async def cb2():
            call_order.append(2)

        kernel.on_shutdown(cb1)
        kernel.on_shutdown(cb2)
        await kernel.stop()
        assert call_order == [1, 2]

    @pytest.mark.asyncio
    async def test_shutdown_callback_error_does_not_block(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()

        async def failing():
            raise RuntimeError("callback failed")

        kernel.on_shutdown(failing)
        success = await kernel.stop()
        assert success is True

    @pytest.mark.asyncio
    async def test_background_services_stopped(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()
        assert len(kernel._background_tasks) == 3
        await kernel.stop()
        assert all(t.done() for t in kernel._background_tasks)

    @pytest.mark.asyncio
    async def test_container_has_services(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()
        assert kernel.container.has("config") is True
        assert kernel.container.has("event_bus") is True
        assert kernel.container.has("command_bus") is True
        assert kernel.container.has("kernel") is True
        await kernel.stop()

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        async with kernel.lifespan():
            assert kernel.state == KernelState.RUNNING
        assert kernel.state == KernelState.STOPPED

    @pytest.mark.asyncio
    async def test_event_bus_works(self):
        config = KernelConfig(name="test")
        kernel = KernelRuntime(config=config)
        await kernel.start()

        received = []

        async def handler(event):
            received.append(event.data["msg"])

        kernel.event_bus.on("test.event", handler)
        await kernel.event_bus.emit("test.event", {"msg": "hello"})
        assert received == ["hello"]
        await kernel.stop()
