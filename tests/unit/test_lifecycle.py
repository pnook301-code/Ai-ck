import pytest
from kernel.lifecycle import LifecycleManager, LifecycleComponent, LifecyclePhase


class TestLifecyclePhase:
    def test_phase_order(self):
        assert LifecyclePhase.CREATED.value == "created"
        assert LifecyclePhase.INITIALIZING.value == "initializing"
        assert LifecyclePhase.INITIALIZED.value == "initialized"
        assert LifecyclePhase.STARTING.value == "starting"
        assert LifecyclePhase.STARTED.value == "started"
        assert LifecyclePhase.READY.value == "ready"
        assert LifecyclePhase.STOPPING.value == "stopping"
        assert LifecyclePhase.STOPPED.value == "stopped"
        assert LifecyclePhase.DESTROYED.value == "destroyed"
        assert LifecyclePhase.ERROR.value == "error"


class TestLifecycleComponent:
    def test_default_phase(self):
        comp = LifecycleComponent(name="test")
        assert comp.phase == LifecyclePhase.CREATED

    def test_with_hooks(self):
        async def init():
            pass

        comp = LifecycleComponent(name="test", on_init=init)
        assert comp.on_init is init

    def test_metadata(self):
        comp = LifecycleComponent(name="test", metadata={"version": "1"})
        assert comp.metadata["version"] == "1"


class TestLifecycleManager:
    @pytest.mark.asyncio
    async def test_register_component(self):
        mgr = LifecycleManager()
        comp = LifecycleComponent(name="svc")
        mgr.register(comp)
        assert mgr.get_component("svc") is comp

    @pytest.mark.asyncio
    async def test_unregister(self):
        mgr = LifecycleManager()
        comp = LifecycleComponent(name="svc")
        mgr.register(comp)
        mgr.unregister("svc")
        assert mgr.get_component("svc") is None

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        mgr = LifecycleManager()
        inited = []

        async def init():
            inited.append("ok")

        comp = LifecycleComponent(name="svc", on_init=init)
        mgr.register(comp)
        await mgr.initialize_all()
        assert inited == ["ok"]
        assert mgr.get_phase() == LifecyclePhase.INITIALIZED

    @pytest.mark.asyncio
    async def test_initialize_sequential(self):
        mgr = LifecycleManager()
        order = []

        async def init1():
            order.append(1)

        async def init2():
            order.append(2)

        mgr.register(LifecycleComponent(name="a", on_init=init1))
        mgr.register(LifecycleComponent(name="b", on_init=init2))
        await mgr.initialize_all(parallel=False)
        assert order == [1, 2]

    @pytest.mark.asyncio
    async def test_start_all(self):
        mgr = LifecycleManager()
        started = []

        async def start():
            started.append("ok")

        comp = LifecycleComponent(name="svc", on_start=start)
        mgr.register(comp)
        await mgr.start_all()
        assert started == ["ok"]
        assert mgr.get_phase() == LifecyclePhase.READY

    @pytest.mark.asyncio
    async def test_stop_all(self):
        mgr = LifecycleManager()
        stopped = []

        async def stop():
            stopped.append("ok")

        comp = LifecycleComponent(name="svc", on_stop=stop)
        mgr.register(comp)
        await mgr.start_all()
        await mgr.stop_all()
        assert stopped == ["ok"]
        assert mgr.get_phase() == LifecyclePhase.STOPPED

    @pytest.mark.asyncio
    async def test_destroy_all(self):
        mgr = LifecycleManager()
        destroyed = []

        async def destroy():
            destroyed.append("ok")

        comp = LifecycleComponent(name="svc", on_destroy=destroy)
        mgr.register(comp)
        await mgr.destroy_all()
        assert destroyed == ["ok"]
        assert comp.phase == LifecyclePhase.DESTROYED

    @pytest.mark.asyncio
    async def test_init_failure(self):
        mgr = LifecycleManager()

        async def fail():
            raise ValueError("init failed")

        comp = LifecycleComponent(name="bad", on_init=fail)
        mgr.register(comp)
        await mgr.initialize_all()
        assert comp.phase == LifecyclePhase.ERROR
        assert comp.error == "init failed"

    @pytest.mark.asyncio
    async def test_start_failure(self):
        mgr = LifecycleManager()

        async def fail():
            raise RuntimeError("start failed")

        comp = LifecycleComponent(name="bad", on_start=fail)
        mgr.register(comp)
        await mgr.start_all()
        assert comp.phase == LifecyclePhase.ERROR

    @pytest.mark.asyncio
    async def test_stop_failure(self):
        mgr = LifecycleManager()

        async def fail():
            raise RuntimeError("stop failed")

        comp = LifecycleComponent(name="bad", on_stop=fail)
        mgr.register(comp)
        await mgr.start_all()
        await mgr.stop_all()
        assert comp.phase == LifecyclePhase.ERROR

    @pytest.mark.asyncio
    async def test_phase_hooks(self):
        mgr = LifecycleManager()
        phases_run = []

        async def on_ready():
            phases_run.append("ready")

        mgr.on_phase(LifecyclePhase.READY, on_ready)
        await mgr.start_all()
        assert "ready" in phases_run

    @pytest.mark.asyncio
    async def test_summary(self):
        mgr = LifecycleManager()
        comp = LifecycleComponent(name="svc")
        mgr.register(comp)
        summary = mgr.summary()
        assert "phase" in summary
        assert "components" in summary
        assert summary["components"]["svc"]["phase"] == "created"

    @pytest.mark.asyncio
    async def test_get_phase(self):
        mgr = LifecycleManager()
        assert mgr.get_phase() == LifecyclePhase.CREATED
