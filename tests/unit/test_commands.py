import pytest
from kernel.commands import Command, CommandBus, CommandResult


class TestCommand:
    def test_create_command(self):
        cmd = Command(name="scan", payload={"target": "x.com"})
        assert cmd.name == "scan"
        assert cmd.payload["target"] == "x.com"
        assert cmd.id is not None

    def test_command_default_payload(self):
        cmd = Command(name="test")
        assert cmd.payload == {}

    def test_command_metadata(self):
        cmd = Command(name="test", metadata={"priority": "high"})
        assert cmd.metadata["priority"] == "high"


class TestCommandResult:
    def test_success_result(self):
        cmd = Command(name="test")
        result = CommandResult(success=True, command=cmd, result="ok")
        assert result.success is True
        assert result.result == "ok"

    def test_error_result(self):
        cmd = Command(name="test")
        result = CommandResult(success=False, command=cmd, error="fail")
        assert result.success is False
        assert result.error == "fail"


class TestCommandBus:
    @pytest.mark.asyncio
    async def test_register_and_dispatch(self):
        bus = CommandBus()

        async def handler(cmd):
            return f"handled {cmd.payload['x']}"

        bus.register("test", handler)
        result = await bus.dispatch(Command(name="test", payload={"x": 1}))
        assert result.success is True
        assert result.result == "handled 1"

    @pytest.mark.asyncio
    async def test_no_handler(self):
        bus = CommandBus()
        result = await bus.dispatch(Command(name="missing"))
        assert result.success is False
        assert "No handler" in result.error

    @pytest.mark.asyncio
    async def test_handler_error(self):
        bus = CommandBus()

        async def failing(cmd):
            raise ValueError("oops")

        bus.register("fail", failing)
        result = await bus.dispatch(Command(name="fail"))
        assert result.success is False
        assert "oops" in result.error

    @pytest.mark.asyncio
    async def test_dispatch_sync(self):
        bus = CommandBus()

        async def handler(cmd):
            return cmd.payload

        bus.register("echo", handler)
        result = await bus.dispatch_sync("echo", {"msg": "hi"})
        assert result.success is True
        assert result.result["msg"] == "hi"

    @pytest.mark.asyncio
    async def test_unregister(self):
        bus = CommandBus()

        async def handler(cmd):
            pass

        bus.register("test", handler)
        assert bus.has_handler("test") is True
        bus.unregister("test")
        assert bus.has_handler("test") is False

    @pytest.mark.asyncio
    async def test_middleware(self):
        bus = CommandBus()
        order = []

        async def mw1(cmd, next_handler):
            order.append("mw1_before")
            result = await next_handler(cmd)
            order.append("mw1_after")
            return result

        async def mw2(cmd, next_handler):
            order.append("mw2_before")
            result = await next_handler(cmd)
            order.append("mw2_after")
            return result

        bus.use(mw1)
        bus.use(mw2)

        async def handler(cmd):
            order.append("handler")
            return "done"

        bus.register("test", handler)
        result = await bus.dispatch(Command(name="test"))
        assert result.result == "done"
        assert order == ["mw1_before", "mw2_before", "handler", "mw2_after", "mw1_after"]

    @pytest.mark.asyncio
    async def test_get_history(self):
        bus = CommandBus()

        async def handler(cmd):
            return "ok"

        bus.register("a", handler)
        await bus.dispatch(Command(name="a"))
        history = bus.get_history()
        assert len(history) == 1
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_clear_history(self):
        bus = CommandBus()

        async def handler(cmd):
            return "ok"

        bus.register("a", handler)
        await bus.dispatch(Command(name="a"))
        bus.clear_history()
        assert len(bus.get_history()) == 0

    @pytest.mark.asyncio
    async def test_emits_event_on_success(self):
        from kernel.events import EventBus

        event_bus = EventBus()
        bus = CommandBus(event_bus=event_bus)
        events = []

        async def on_completed(event):
            events.append(event)

        event_bus.on("command.completed", on_completed)

        async def handler(cmd):
            return "done"

        bus.register("ok", handler)
        await bus.dispatch(Command(name="ok"))
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_emits_event_on_failure(self):
        from kernel.events import EventBus

        event_bus = EventBus()
        bus = CommandBus(event_bus=event_bus)
        events = []

        async def on_failed(event):
            events.append(event)

        event_bus.on("command.failed", on_failed)

        async def handler(cmd):
            raise RuntimeError("fail")

        bus.register("fail", handler)
        await bus.dispatch(Command(name="fail"))
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_duration_recorded(self):
        bus = CommandBus()

        async def slow(cmd):
            await asyncio.sleep(0.01)
            return "done"

        bus.register("slow", slow)
        result = await bus.dispatch(Command(name="slow"))
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_has_handler(self):
        bus = CommandBus()
        assert bus.has_handler("x") is False

        async def h(cmd):
            pass

        bus.register("x", h)
        assert bus.has_handler("x") is True
