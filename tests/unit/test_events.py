import asyncio
import pytest
from kernel.events import Event, EventBus


class TestEvent:
    def test_create_event(self):
        event = Event(name="test.event", data={"key": "value"})
        assert event.name == "test.event"
        assert event.data["key"] == "value"
        assert event.id is not None
        assert event.timestamp > 0

    def test_event_default_data(self):
        event = Event(name="test")
        assert event.data == {}

    def test_event_default_source(self):
        event = Event(name="test")
        assert event.source == "kernel"


class TestEventBus:
    @pytest.mark.asyncio
    async def test_on_and_emit(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.on("test.event", handler)
        await bus.emit("test.event", {"msg": "hello"})
        assert len(received) == 1
        assert received[0].data["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_wildcard_handler(self):
        bus = EventBus()
        received = []

        async def wildcard(event):
            received.append(event.name)

        bus.on("*", wildcard)
        await bus.emit("any.event")
        await bus.emit("another.event")
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_off_by_name(self):
        bus = EventBus()

        async def handler(event):
            pass

        bus.on("test", handler)
        assert bus.listeners("test") == 1
        bus.off("test")
        assert bus.listeners("test") == 0

    @pytest.mark.asyncio
    async def test_off_specific_handler(self):
        bus = EventBus()

        async def h1(event):
            pass

        async def h2(event):
            pass

        bus.on("test", h1)
        bus.on("test", h2)
        assert bus.listeners("test") == 2
        bus.off("test", h1)
        assert bus.listeners("test") == 1

    @pytest.mark.asyncio
    async def test_once(self):
        bus = EventBus()
        count = 0

        async def handler(event):
            nonlocal count
            count += 1

        bus.once("test", handler)
        await bus.emit("test")
        await bus.emit("test")
        assert count == 1

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash(self):
        bus = EventBus()

        async def failing(event):
            raise ValueError("boom")

        async def good(event):
            pass

        bus.on("test", failing)
        bus.on("test", good)
        await bus.emit("test")

    @pytest.mark.asyncio
    async def test_parent_event_dispatch(self):
        bus = EventBus()
        received = []

        async def parent(event):
            received.append(event.name)

        bus.on("parent", parent)
        await bus.emit("parent.child")
        assert "parent.child" in received

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        bus = EventBus()
        await bus.start()
        assert bus._running is True
        await bus.stop()
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_listeners_count(self):
        bus = EventBus()

        async def h1(event):
            pass

        async def h2(event):
            pass

        assert bus.listeners() == 0
        bus.on("a", h1)
        bus.on("b", h2)
        bus.on("*", h1)
        assert bus.listeners() == 3

    @pytest.mark.asyncio
    async def test_emit_async(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event.data)
            return

        bus.on("test", handler)
        await bus.start()
        await bus.emit_async("test", {"delayed": True})
        await asyncio.sleep(0.05)
        assert len(received) > 0

    @pytest.mark.asyncio
    async def test_safe_dispatch_error_logged(self, test_logger):
        bus = EventBus(logger=test_logger)

        async def failing(event):
            raise RuntimeError("fail")

        event = Event(name="test")
        await bus._safe_dispatch(failing, event)

    @pytest.mark.asyncio
    async def test_emit_no_handlers_no_error(self):
        bus = EventBus()
        await bus.emit("nonexistent")
