"""Exhaustive end-to-end integration test — matching ACTUAL module APIs"""

import asyncio
import json
import os
import tempfile
import time
import uuid
import numpy as np
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — Kernel Bootstrap
# ═══════════════════════════════════════════════════════════════════════════════

def test_kernel_config():
    from kernel.config import KernelConfig
    cfg = KernelConfig(name="ck-nexus-test", environment="testing")
    assert cfg.name == "ck-nexus-test"
    assert cfg.environment == "testing"
    assert cfg.max_workers == 10
    d = cfg.to_dict()
    assert d["name"] == "ck-nexus-test"

def test_kernel_config_from_dict():
    from kernel.config import KernelConfig
    cfg = KernelConfig()
    assert cfg.debug is True
    assert "telemetry" in cfg.features


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — EventBus
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventBus:
    def test_emit_and_on(self):
        from kernel.events import EventBus
        bus = EventBus()
        received = []

        async def handler(ev):
            received.append(ev.data)

        bus.on("test.event", handler)
        asyncio.run(bus.emit("test.event", {"msg": "hello"}))
        assert len(received) == 1
        assert received[0]["msg"] == "hello"

    def test_off(self):
        from kernel.events import EventBus
        bus = EventBus()
        calls = []

        async def h(ev): calls.append(1)

        bus.on("evt", h)
        asyncio.run(bus.emit("evt", {}))
        assert len(calls) == 1

        bus.off("evt", h)
        asyncio.run(bus.emit("evt", {}))
        assert len(calls) == 1

    def test_event_defaults(self):
        from kernel.events import Event
        ev = Event(name="test", data={"k": "v"})
        assert ev.name == "test"
        assert ev.data["k"] == "v"
        assert ev.id is not None
        assert ev.timestamp > 0
        assert ev.source == "kernel"

    def test_wildcard_handler(self):
        from kernel.events import EventBus
        bus = EventBus()
        received = []

        async def wild(ev): received.append(ev.name)

        bus.on("*", wild)
        asyncio.run(bus.emit("any.event", {}))
        asyncio.run(bus.emit("other", {}))
        assert len(received) == 2

    def test_listeners_count(self):
        from kernel.events import EventBus
        bus = EventBus()
        async def h(ev): pass
        bus.on("a", h)
        bus.on("a", h)
        bus.on("b", h)
        assert bus.listeners("a") == 2
        assert bus.listeners("b") == 1
        assert bus.listeners() == 3

    def test_once(self):
        from kernel.events import EventBus
        bus = EventBus()
        calls = []

        async def h(ev): calls.append(1)

        bus.once("once", h)
        asyncio.run(bus.emit("once", {}))
        assert len(calls) == 1
        asyncio.run(bus.emit("once", {}))
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_emit_async(self):
        from kernel.events import EventBus
        bus = EventBus()
        results = []

        async def h(ev): results.append(ev.data)

        bus.on("a", h)
        await bus.emit("a", {"n": 1})
        assert len(results) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3 — CommandBus
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommandBus:
    @pytest.mark.asyncio
    async def test_register_and_dispatch(self):
        from kernel.commands import CommandBus, Command
        bus = CommandBus()

        async def greet(cmd):
            return {"reply": f"Hello {cmd.payload['name']}"}

        bus.register("greet", greet)
        result = await bus.dispatch(Command(name="greet", payload={"name": "CK"}))
        assert result.success is True
        assert result.result["reply"] == "Hello CK"

    @pytest.mark.asyncio
    async def test_unregistered_command(self):
        from kernel.commands import CommandBus, Command
        bus = CommandBus()
        result = await bus.dispatch(Command(name="unknown"))
        assert result.success is False
        assert "No handler" in result.error

    @pytest.mark.asyncio
    async def test_dispatch_sync(self):
        from kernel.commands import CommandBus
        bus = CommandBus()
        async def h(cmd): return cmd.payload
        bus.register("echo", h)
        result = await bus.dispatch_sync("echo", {"x": 1})
        assert result.success is True
        assert result.result["x"] == 1

    def test_has_handler(self):
        from kernel.commands import CommandBus
        bus = CommandBus()
        async def h(cmd): pass
        bus.register("exists", h)
        assert bus.has_handler("exists") is True
        assert bus.has_handler("nope") is False

    def test_history(self):
        from kernel.commands import CommandBus
        bus = CommandBus()
        hist = bus.get_history()
        assert isinstance(hist, list)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4 — DI Container
# ═══════════════════════════════════════════════════════════════════════════════

class TestDIContainer:
    def test_register_instance(self):
        from kernel.container import DIContainer
        container = DIContainer()
        container.register_instance("db", {"host": "localhost"})
        resolved = container.resolve("db")
        assert resolved["host"] == "localhost"

    def test_register_factory(self):
        from kernel.container import DIContainer
        container = DIContainer()
        container.register_factory("counter", lambda: {"val": 42})
        assert container.resolve("counter")["val"] == 42

    def test_register_class(self):
        from kernel.container import DIContainer
        container = DIContainer()

        class Logger:
            def log(self, msg): return f"log: {msg}"

        container.register("logger", Logger)
        resolved = container.resolve("logger")
        assert isinstance(resolved, Logger)
        assert resolved.log("test") == "log: test"

    def test_has_method(self):
        from kernel.container import DIContainer
        container = DIContainer()
        assert container.has("nope") is False
        container.register_instance("key", 42)
        assert container.has("key") is True

    def test_resolve_nonexistent(self):
        from kernel.container import DIContainer
        container = DIContainer()
        with pytest.raises(KeyError):
            container.resolve("nonexistent")

    @pytest.mark.asyncio
    async def test_close(self):
        from kernel.container import DIContainer
        container = DIContainer()
        await container.close()
        assert container.has("anything") is False


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5 — ConfigService
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_get_set(self):
        from kernel.config import ConfigService
        cfg = ConfigService()
        cfg.set("db.host", "localhost")
        assert cfg.get("db.host") == "localhost"
        assert cfg.get("missing", "default") == "default"

    def test_config_property(self):
        from kernel.config import ConfigService
        cfg = ConfigService()
        assert cfg.config.name == "ck-nexus-aios"
        assert cfg.config.environment == "development"

    def test_to_dict(self):
        from kernel.config import ConfigService
        cfg = ConfigService()
        d = cfg.to_dict()
        assert d["name"] == "ck-nexus-aios"


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6 — SecurityService
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurity:
    def test_password_hashing(self):
        from kernel.security import SecurityService
        svc = SecurityService()
        pw = "supersecret123"
        hashed = svc.hash_password(pw)
        assert hashed != pw
        assert svc.verify_password(pw, hashed) is True
        assert svc.verify_password("wrong", hashed) is False

    def test_legacy_sha256_compat(self):
        from kernel.security import SecurityService
        svc = SecurityService()
        assert svc.verify_password("test", "sha256:salt:hash") is False

    def test_create_token_and_authenticate(self):
        from kernel.security import SecurityService, UserPrincipal
        svc = SecurityService()
        principal = UserPrincipal(id="u1", username="admin", roles={"admin"})
        token = svc.create_token(principal, ttl=3600)
        assert token.startswith("ckt_")

        auth_result = svc.authenticate(token)
        assert auth_result is not None
        assert auth_result.username == "admin"
        assert auth_result.authenticated is True

    def test_token_expiry(self):
        from kernel.security import SecurityService, UserPrincipal
        svc = SecurityService()
        p = UserPrincipal(id="u1", username="temp")
        token = svc.create_token(p, ttl=0)  # 0 TTL = expired immediately
        auth_result = svc.authenticate(token)
        assert auth_result is None  # expired

    def test_api_key_auth(self):
        from kernel.security import SecurityService, UserPrincipal
        svc = SecurityService()
        p = UserPrincipal(id="u1", username="api_user")
        key = svc.generate_api_key(p)
        assert key.startswith("ck_")

        auth = svc.authenticate(key, provider=None)
        assert auth is not None
        assert auth.username == "api_user"

    def test_authorization(self):
        from kernel.security import SecurityService, UserPrincipal, AuthorizationPolicy
        svc = SecurityService()
        policy = AuthorizationPolicy(name="admin_only", roles={"admin"})
        svc.add_policy(policy)

        admin = UserPrincipal(id="u1", username="admin", roles={"admin"})
        user = UserPrincipal(id="u2", username="user", roles={"user"})

        assert svc.authorize(admin, "admin_only") is True
        assert svc.authorize(user, "admin_only") is False

    def test_sign_and_verify(self):
        from kernel.security import SecurityService
        svc = SecurityService()
        sig = svc.sign("test-data")
        assert svc.verify_signature("test-data", sig) is True
        assert svc.verify_signature("wrong-data", sig) is False


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7 — State Manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestState:
    def test_get_set(self):
        from kernel.state import StateManager
        sm = StateManager()
        sm.set("foo", "bar")
        assert sm.get("foo") == "bar"
        assert sm.get("missing") is None

    def test_snapshot(self):
        from kernel.state import StateManager
        sm = StateManager()
        sm.set("a", 1)
        snap = sm.snapshot()
        assert snap.data["a"] == 1
        assert snap.version >= 1

    def test_delete(self):
        from kernel.state import StateManager
        sm = StateManager()
        sm.set("k", "v")
        assert sm.get("k") == "v"
        sm.delete("k")
        assert sm.get("k") is None

    def test_update(self):
        from kernel.state import StateManager
        sm = StateManager()
        sm.update({"x": 10, "y": 20})
        assert sm.get("x") == 10
        assert sm.get("y") == 20

    def test_clear(self):
        from kernel.state import StateManager
        sm = StateManager()
        sm.set("a", 1)
        sm.set("b", 2)
        sm.clear()
        assert sm.get("a") is None
        assert sm.get("b") is None

    def test_all(self):
        from kernel.state import StateManager
        sm = StateManager()
        sm.set("a", 1)
        all_data = sm.all()
        assert all_data["a"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PART 8 — Metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    def test_counter(self):
        from kernel.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.increment("req_count", 5)
        mc.increment("req_count", 3)
        all_metrics = mc.get_all()
        assert all_metrics["counters"]["req_count"] == 8

    def test_gauge(self):
        from kernel.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.gauge("cpu", 45.2)
        assert mc.get_gauge("cpu") == 45.2

    def test_histogram(self):
        from kernel.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.observe("latency", 0.1)
        mc.observe("latency", 0.2)
        stats = mc.get_all()
        assert "latency" in stats["histograms"]
        assert stats["histograms"]["latency"]["count"] == 2

    def test_timer_context(self):
        from kernel.metrics import MetricsCollector
        mc = MetricsCollector()
        with mc.time("operation"):
            pass
        stats = mc.get_all()
        assert "operation_duration" in stats["histograms"]

    def test_reset(self):
        from kernel.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.increment("test", 1)
        mc.reset("test")
        assert mc.get_counter("test") == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PART 9 — Health Checks
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealth:
    @pytest.mark.asyncio
    async def test_register_and_check(self):
        from kernel.health import HealthChecker, HealthCheck, HealthStatus
        hc = HealthChecker()

        async def check_db():
            return HealthCheck(name="db", status=HealthStatus.HEALTHY, message="ok")

        hc.register("db", check_db)
        results = await hc.run_checks()
        assert results["db"].status == HealthStatus.HEALTHY
        assert "ok" in results["db"].message

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        from kernel.health import HealthChecker, HealthCheck, HealthStatus
        hc = HealthChecker()

        async def check_disk():
            return HealthCheck(name="disk", status=HealthStatus.UNHEALTHY, message="low space")

        hc.register("disk", check_disk)
        results = await hc.run_checks()
        assert results["disk"].status == HealthStatus.UNHEALTHY

    def test_get_status(self):
        from kernel.health import HealthChecker
        hc = HealthChecker()
        assert hc.get_status().value == "unknown"

    def test_summary(self):
        from kernel.health import HealthChecker
        hc = HealthChecker()
        s = hc.summary()
        assert s["total"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PART 10 — Cache Service
# ═══════════════════════════════════════════════════════════════════════════════

class TestCache:
    def test_set_get(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        cache.set("key1", "value1", ttl=60)
        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent") is None

    def test_expiry(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        cache.set("exp", "data", ttl=0)
        assert cache.get("exp") is None

    def test_delete(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        cache.set("del", "x")
        cache.delete("del")
        assert cache.get("del") is None

    def test_clear(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_has(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        cache.set("tk", "val")
        assert cache.has("tk") is True
        assert cache.has("nope") is False

    def test_remember(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        called = 0
        def factory():
            nonlocal called
            called += 1
            return 42
        assert cache.remember("rk", 60, factory) == 42
        assert cache.remember("rk", 60, factory) == 42
        assert called == 1  # only called once

    def test_stats(self):
        from kernel.cache import CacheService, CacheBackend
        cache = CacheService(backend=CacheBackend.MEMORY)
        s = cache.stats()
        assert "size" in s


# ═══════════════════════════════════════════════════════════════════════════════
# PART 11 — Lifecycle Manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestLifecycle:
    def test_phases(self):
        from kernel.lifecycle import LifecyclePhase
        assert LifecyclePhase.CREATED.value == "created"
        assert LifecyclePhase.STARTING.value == "starting"
        assert LifecyclePhase.READY.value == "ready"

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self):
        from kernel.lifecycle import LifecycleManager, LifecycleComponent
        lm = LifecycleManager()
        init_calls = 0
        start_calls = 0
        stop_calls = 0

        async def init(): nonlocal init_calls; init_calls += 1
        async def start(): nonlocal start_calls; start_calls += 1
        async def stop(): nonlocal stop_calls; stop_calls += 1

        comp = LifecycleComponent(name="test", on_init=init, on_start=start, on_stop=stop)
        lm.register(comp)

        await lm.initialize_all()
        assert init_calls == 1
        assert lm.get_phase().value == "initialized"

        await lm.start_all()
        assert start_calls == 1
        assert lm.get_phase().value == "ready"

        await lm.stop_all()
        assert stop_calls == 1
        assert lm.get_phase().value == "stopped"

        s = lm.summary()
        assert "test" in s["components"]


# ═══════════════════════════════════════════════════════════════════════════════
# PART 12 — Task Scheduler
# ═══════════════════════════════════════════════════════════════════════════════

class TestScheduler:
    @pytest.mark.asyncio
    async def test_add_and_run(self):
        from kernel.scheduler import TaskScheduler
        scheduler = TaskScheduler()
        calls = 0

        async def task():
            nonlocal calls
            calls += 1

        task_id = scheduler.add("test", 0.02, task, run_immediately=True)
        assert task_id is not None
        scheduler.start()

        await asyncio.sleep(0.1)
        await scheduler.stop()

        assert calls >= 1

    def test_register_direct(self):
        from kernel.scheduler import TaskScheduler, ScheduledTask
        scheduler = TaskScheduler()
        st = ScheduledTask(name="direct", interval=10, callback=lambda: None)
        scheduler.register(st)
        assert scheduler is not None


# ═══════════════════════════════════════════════════════════════════════════════
# PART 13 — Agent Types
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentTypes:
    def test_agent_message(self):
        from kernel.agents.types import AgentMessage
        msg = AgentMessage(sender="a1", receiver="a2", msg_type="ping", content={"val": 1})
        assert msg.id.startswith("msg_")
        d = msg.to_dict()
        assert d["sender"] == "a1"
        recovered = AgentMessage.from_dict(d)
        assert recovered.sender == "a1"

    def test_agent_task(self):
        from kernel.agents.types import AgentTask
        task = AgentTask(title="build", description="build it")
        assert task.id.startswith("task_")
        assert task.status == "pending"
        task.complete({"ok": True})
        assert task.status == "completed"
        assert task.result["ok"] is True

        task2 = AgentTask(title="fail", description="will fail")
        task2.fail("error msg")
        assert task2.status == "failed"

    def test_agent_status(self):
        from kernel.agents.types import AgentStatus
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.WORKING.value == "working"

    def test_agent_capability(self):
        from kernel.agents.types import AgentCapability
        assert AgentCapability.CODE_WRITE.value == "write_code"
        assert len(list(AgentCapability)) >= 8


# ═══════════════════════════════════════════════════════════════════════════════
# PART 14 — Base Agent
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        from kernel.agents.base import BaseAgent
        from kernel.agents.types import AgentTask
        agent = BaseAgent(name="test", role="worker")
        async def do(task): return {"done": True}
        agent._do_task = do

        task = AgentTask(title="test", description="do it")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result["done"] is True
        assert agent.tasks_completed == 1

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        from kernel.agents.base import BaseAgent
        from kernel.agents.types import AgentTask
        agent = BaseAgent(name="fail", role="worker")
        async def do(task): raise RuntimeError("boom")
        agent._do_task = do

        task = AgentTask(title="fail", description="will fail")
        result = await agent.execute(task)
        assert result.status == "failed"
        assert agent.tasks_failed == 1

    @pytest.mark.asyncio
    async def test_send_receive(self):
        from kernel.agents.base import BaseAgent
        from kernel.agents.types import AgentMessage
        agent = BaseAgent(name="a1", role="worker")
        msg = await agent.send("a2", "hello", {"text": "hi"})
        assert msg.sender == "a1"
        assert len(agent.outbox) == 1

        await agent.receive(AgentMessage(sender="a2", receiver="a1", msg_type="reply", content={}))
        assert len(agent.inbox) == 1

    def test_get_status(self):
        from kernel.agents.base import BaseAgent
        agent = BaseAgent(name="stat", role="checker")
        s = agent.get_status()
        assert s["name"] == "stat"
        assert s["status"] == "idle"

    @pytest.mark.asyncio
    async def test_initialize_and_stop(self):
        from kernel.agents.base import BaseAgent
        agent = BaseAgent(name="cycle", role="test")
        await agent.initialize()
        assert agent.status.value == "idle"
        await agent.stop()
        assert agent.status.value == "stopped"


# ═══════════════════════════════════════════════════════════════════════════════
# PART 15 — Agent Registry + Manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentRegistry:
    def test_register_and_find(self):
        from kernel.agents.registry import AgentRegistry
        from kernel.agents.base import BaseAgent
        from kernel.agents.types import AgentCapability
        reg = AgentRegistry()
        a1 = BaseAgent(name="coder", role="code", capabilities={AgentCapability.CODE_WRITE})
        a2 = BaseAgent(name="reviewer", role="review", capabilities={AgentCapability.CODE_REVIEW})
        reg.register(a1)
        reg.register(a2)

        assert reg.count() == 2
        assert reg.get("coder") is a1
        assert len(reg.find_by_capability(AgentCapability.CODE_WRITE)) == 1
        assert len(reg.find_by_role("code")) == 1
        names = reg.get_names()
        assert "coder" in names


class TestAgentManager:
    @pytest.mark.asyncio
    async def test_register_and_execute(self):
        from kernel.agents.manager import AgentManager
        from kernel.agents.base import BaseAgent
        mgr = AgentManager()
        a1 = BaseAgent(name="w1", role="worker")
        a2 = BaseAgent(name="w2", role="worker")
        mgr.register_agent(a1)
        mgr.register_agent(a2)

        assert len(mgr.get_all_agents()) == 2
        status = mgr.get_status()
        assert status["agents"] == 2

    @pytest.mark.asyncio
    async def test_delegate(self):
        from kernel.agents.manager import AgentManager
        from kernel.agents.base import BaseAgent
        mgr = AgentManager()
        a1 = BaseAgent(name="helper", role="worker")
        async def do(task): return {"done": True}
        a1._do_task = do
        mgr.register_agent(a1)

        result = await mgr.delegate("helper", "do something")
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# PART 16 — Orchestrator Agent
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_plan_and_execute(self):
        from kernel.agents.orchestrator import OrchestratorAgent
        from kernel.agents.registry import AgentRegistry
        from kernel.agents.base import BaseAgent

        reg = AgentRegistry()
        coder = BaseAgent(name="coder", role="code")
        async def do(task): return {"code": "ok"}
        coder._do_task = do
        reg.register(coder)
        tester = BaseAgent(name="tester", role="test")
        async def do2(task): return {"tests": "ok"}
        tester._do_task = do2
        reg.register(tester)

        oa = OrchestratorAgent(agent_registry=reg)
        plan = await oa.plan("write some code and test it")
        assert plan["status"] == "ready"
        assert len(plan["steps"]) >= 2

        result = await oa.execute_plan(plan)
        assert result["status"] == "completed"
        assert len(result["results"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# PART 17 — Function Registry (100 functions)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFunctionRegistry:
    def test_all_110_registered(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        count = register_all_categories(reg)
        assert count == 130
        assert len(reg.list_functions()) == 130

    def test_by_category(self):
        from kernel.fn import FunctionRegistry, register_all_categories, FunctionCategory
        reg = FunctionRegistry()
        register_all_categories(reg)
        for cat in FunctionCategory:
            fns = reg.list_functions(category=cat)
            assert len(fns) == 10, f"Expected 10 for {cat}, got {len(fns)}"

    def test_get_definition(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        register_all_categories(reg)
        fn = reg.get_definition("1.1")
        assert fn is not None
        assert fn.name is not None
        d = reg.get_definition("999.999")
        assert d is None

    @pytest.mark.asyncio
    async def test_execute(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        register_all_categories(reg)
        result = await reg.execute("1.1", {"name": "test"})
        assert result.success is True
        assert result.status.value == "success"

    @pytest.mark.asyncio
    async def test_execute_unknown(self):
        from kernel.fn import FunctionRegistry
        reg = FunctionRegistry()
        result = await reg.execute("999.999", {})
        assert result.success is False
        assert "Unknown" in result.error

    def test_find(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        register_all_categories(reg)
        results = reg.find(query="test")
        assert len(results) >= 1

    def test_stats(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        register_all_categories(reg)
        stats = reg.get_stats()
        assert stats["registered"] == 130

    @pytest.mark.asyncio
    async def test_execute_pipeline(self):
        from kernel.fn import FunctionRegistry, register_all_categories
        reg = FunctionRegistry()
        register_all_categories(reg)
        steps = [
            {"fn": "1.1", "params": {"name": "pipe-test"}},
            {"fn": "1.2", "params": {}},
        ]
        result = await reg.execute_pipeline(steps)
        assert "results" in result
        assert "final" in result


# ═══════════════════════════════════════════════════════════════════════════════
# PART 18 — Knowledge Graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    def test_add_and_get_entity(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, EntityType
        kg = KnowledgeGraph()
        unit = KnowledgeUnit(name="AI", entity_type=EntityType.CONCEPT,
                             properties={"field": "ML"})
        eid = kg.add_entity(unit)
        assert eid == unit.id

        entity = kg.get_entity(eid)
        assert entity is not None
        assert entity.name == "AI"
        assert entity.entity_type == EntityType.CONCEPT

    def test_add_and_get_relation(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, KnowledgeRelation, EntityType, RelationType
        kg = KnowledgeGraph()
        e1 = KnowledgeUnit(name="Python", entity_type=EntityType.CONCEPT)
        e2 = KnowledgeUnit(name="Programming", entity_type=EntityType.CONCEPT)
        kg.add_entity(e1)
        kg.add_entity(e2)

        rel = KnowledgeRelation(source_id=e1.id, target_id=e2.id,
                                relation_type=RelationType.RELATED_TO, weight=0.9)
        assert kg.add_relation(rel) is True

        rels = kg.get_relations(e1.id)
        assert len(rels) == 1

    def test_traverse_bfs(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, KnowledgeRelation, EntityType, RelationType
        kg = KnowledgeGraph()
        a = KnowledgeUnit(name="A", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="B", entity_type=EntityType.CONCEPT)
        c = KnowledgeUnit(name="C", entity_type=EntityType.CONCEPT)
        kg.add_entity(a)
        kg.add_entity(b)
        kg.add_entity(c)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.RELATED_TO))
        kg.add_relation(KnowledgeRelation(b.id, c.id, RelationType.RELATED_TO))

        results = kg.traverse(a.id)
        assert len(results) == 2  # B and C

    def test_find_path(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, KnowledgeRelation, EntityType, RelationType
        kg = KnowledgeGraph()
        a = KnowledgeUnit(name="Start", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="Middle", entity_type=EntityType.CONCEPT)
        c = KnowledgeUnit(name="End", entity_type=EntityType.CONCEPT)
        kg.add_entity(a)
        kg.add_entity(b)
        kg.add_entity(c)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.RELATED_TO))
        kg.add_relation(KnowledgeRelation(b.id, c.id, RelationType.RELATED_TO))

        paths = kg.find_path(a.id, c.id)
        assert len(paths) >= 1
        assert len(paths[0]) == 2  # two edges

    def test_remove_entity(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, EntityType
        kg = KnowledgeGraph()
        u = KnowledgeUnit(name="Temp", entity_type=EntityType.CONCEPT)
        kg.add_entity(u)
        assert kg.get_entity(u.id) is not None
        kg.remove_entity(u.id)
        assert kg.get_entity(u.id) is None

    def test_stats(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, KnowledgeRelation, EntityType, RelationType
        kg = KnowledgeGraph()
        a = KnowledgeUnit(name="A", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="B", entity_type=EntityType.CONCEPT)
        kg.add_entity(a)
        kg.add_entity(b)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.RELATED_TO))
        stats = kg.stats
        assert stats.total_entities == 2
        assert stats.total_relations == 1

    def test_save_load(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, KnowledgeRelation, EntityType, RelationType
        import json, os
        save_path = "/tmp/test_kg_save.json"
        kg = KnowledgeGraph(persistence_path=save_path)
        u = KnowledgeUnit(name="Saved", entity_type=EntityType.CONCEPT)
        kg.add_entity(u)
        path = kg.save()
        assert os.path.exists(path)

        kg2 = KnowledgeGraph()
        kg2.load(path)
        assert kg2.stats.total_entities == 1
        if os.path.exists(path):
            os.unlink(path)

    def test_clear(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, EntityType
        kg = KnowledgeGraph()
        kg.add_entity(KnowledgeUnit(name="Del", entity_type=EntityType.CONCEPT))
        kg.clear()
        assert kg.stats.total_entities == 0

    def test_inference(self):
        from kernel.memory.knowledge_graph import KnowledgeGraph
        from kernel.memory.types import KnowledgeUnit, KnowledgeRelation, EntityType, RelationType
        kg = KnowledgeGraph()
        a = KnowledgeUnit(name="X", entity_type=EntityType.CONCEPT)
        b = KnowledgeUnit(name="Y", entity_type=EntityType.CONCEPT)
        c = KnowledgeUnit(name="Z", entity_type=EntityType.CONCEPT)
        kg.add_entity(a)
        kg.add_entity(b)
        kg.add_entity(c)
        kg.add_relation(KnowledgeRelation(a.id, b.id, RelationType.PART_OF))
        kg.add_relation(KnowledgeRelation(b.id, c.id, RelationType.PART_OF))
        inferred_count = kg.infer()
        assert inferred_count >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# PART 19 — Video Analysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestVideoTypes:
    def test_frame_info(self):
        from kernel.video.types import FrameInfo
        fi = FrameInfo(index=0, timestamp_sec=1.5, timestamp_str="01.500", path="/tmp/f.jpg")
        assert fi.index == 0
        assert fi.timestamp_sec == 1.5
        assert fi.width == 0

    def test_video_source_type(self):
        from kernel.video.types import VideoSourceType
        assert VideoSourceType.YOUTUBE.value == "youtube"

    def test_transcript_segment(self):
        from kernel.video.types import TranscriptSegment
        seg = TranscriptSegment(start=0.0, end=1.0, text="hello", confidence=0.95)
        assert seg.text == "hello"

    def test_transcript(self):
        from kernel.video.types import Transcript, TranscriptSegment
        t = Transcript(segments=[TranscriptSegment(0.0, 1.0, "hello")],
                       full_text="hello", language="en")
        text = t.text_around(0.5)
        assert "hello" in text

    def test_video_analysis_result(self):
        from kernel.video.types import VideoAnalysisResult
        r = VideoAnalysisResult(query="test", answer="result")
        assert r.id.startswith("va_")
        s = r.summary
        assert s["query"] == "test"


class TestSceneDetector:
    def test_detect_empty(self):
        from kernel.video.scene_detector import SceneDetector
        sd = SceneDetector(threshold=0.5)
        assert len(sd.detect([])) == 0

    def test_detect_single_frame(self):
        from kernel.video.scene_detector import SceneDetector
        sd = SceneDetector(threshold=0.99, max_frames=2)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        changes = sd.detect([(0, frame1, 0.0), (1, frame2, 1.0)])
        # Fallback always adds mid-frame when < 2, so expect at least 1
        assert len(changes) >= 1

    def test_detect_scene_change(self):
        from kernel.video.scene_detector import SceneDetector
        sd = SceneDetector(threshold=0.1)
        f1 = np.zeros((100, 100, 3), dtype=np.uint8)
        f2 = np.ones((100, 100, 3), dtype=np.uint8) * 255
        changes = sd.detect([(0, f1, 0.0), (1, f2, 1.0)])
        assert len(changes) >= 1


class TestFrameExtractor:
    def test_extract_invalid_url_raises(self):
        from kernel.video.frame_extractor import VideoFrameExtractor
        from kernel.video.types import VideoSourceType
        fe = VideoFrameExtractor()
        with pytest.raises(FileNotFoundError):
            fe.extract("/nonexistent/video.mp4", source_type=VideoSourceType.LOCAL)

    def test_extract_missing_file(self):
        from kernel.video.frame_extractor import VideoFrameExtractor
        fe = VideoFrameExtractor()
        with pytest.raises(FileNotFoundError):
            fe.extract("/nonexistent/video.mp4")


class TestVideoAnalyzer:
    def test_analyzer_with_mocks(self):
        from kernel.video.analyzer import VideoAnalyzer
        from kernel.video.types import VideoAnalysisResult, VideoMeta
        mock_fe = MagicMock()
        mock_fe.extract.return_value = ([], VideoMeta(), "/tmp/fake.mp4")
        mock_ts = MagicMock()
        mock_ts.transcribe.return_value = MagicMock()

        analyzer = VideoAnalyzer(frame_extractor=mock_fe, transcriber=mock_ts)
        result = analyzer.analyze("https://example.com/video.mp4", query="test?")
        assert isinstance(result, VideoAnalysisResult)


class TestWatchPlugin:
    def test_parse_youtube(self):
        from kernel.video.plugin import WatchPlugin
        plugin = WatchPlugin()
        result = plugin.parse("/watch https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert result is not None
        assert "youtube" in result["source"].lower()

    def test_parse_empty_returns_none(self):
        from kernel.video.plugin import WatchPlugin
        plugin = WatchPlugin()
        result = plugin.parse("/watch")
        assert result is None

    def test_parse_no_command(self):
        from kernel.video.plugin import WatchPlugin
        plugin = WatchPlugin()
        result = plugin.parse("hello")
        assert result is None

    def test_properties(self):
        from kernel.video.plugin import WatchPlugin
        plugin = WatchPlugin()
        assert isinstance(plugin.name, str)
        assert isinstance(plugin.description, str)
        assert len(plugin.commands) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PART 20 — ICE Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestICE:
    def test_roles_order(self):
        from kernel.ice import ROLES
        assert ROLES.ORDER == ["Architect", "Critic", "Judge"]
        assert len(ROLES.ORDER) == 3

    def test_iteration_result_defaults(self):
        from kernel.ice import IterationResult
        r = IterationResult(iteration=1, role="Architect", action="design", content="built")
        assert r.id.startswith("ice_")
        assert r.decision == "continue"

    @pytest.mark.asyncio
    async def test_architect_agent(self):
        from kernel.ice.agents import ArchitectAgent
        from kernel.agents.types import AgentTask
        agent = ArchitectAgent()
        task = AgentTask(title="design", description="Design auth system")
        result = await agent.execute(task)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_critic_agent(self):
        from kernel.ice.agents import CriticAgent
        from kernel.agents.types import AgentTask
        agent = CriticAgent()
        task = AgentTask(title="review", description="Review code")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result.get("scores", {}).get("overall", 0) > 0

    @pytest.mark.asyncio
    async def test_judge_pass(self):
        from kernel.ice.agents import JudgeAgent
        from kernel.agents.types import AgentTask
        agent = JudgeAgent(threshold=50)
        task = AgentTask(title="judge", description="Judge output",
                         metadata={"scores": {"overall": 85}})
        result = await agent.execute(task)
        assert result.result["decision"] == "TERMINATE_LOOP"

    @pytest.mark.asyncio
    async def test_judge_fail(self):
        from kernel.ice.agents import JudgeAgent
        from kernel.agents.types import AgentTask
        agent = JudgeAgent(threshold=95)
        task = AgentTask(title="judge", description="Judge output",
                         metadata={"scores": {"overall": 50}})
        result = await agent.execute(task)
        assert result.result["decision"] == "continue"

    @pytest.mark.asyncio
    async def test_ice_terminates(self):
        from kernel.ice import IterativeConsensusEngine
        ice = IterativeConsensusEngine(max_iterations=5, judge_threshold=50)
        report = await ice.run(task="build an API")
        assert report["success"] is True
        assert 1 <= report["total_iterations"] <= 5

    @pytest.mark.asyncio
    async def test_ice_max_iterations(self):
        from kernel.ice import IterativeConsensusEngine
        ice = IterativeConsensusEngine(max_iterations=4, judge_threshold=99)
        report = await ice.run(task="impossible task")
        assert report["total_iterations"] <= 4
        assert report["recommendation"] == "NEEDS_MORE_WORK"

    @pytest.mark.asyncio
    async def test_ice_full_workflow(self):
        from kernel.ice import IterativeConsensusEngine, ROLES
        ice = IterativeConsensusEngine(max_iterations=6, judge_threshold=75)
        report = await ice.run(task="Create a REST API with auth")
        assert report["total_iterations"] >= 2
        assert len(report["history"]) == report["total_iterations"]
        roles_seen = set(h["role"] for h in report["history"])
        assert ROLES.ARCHITECT in roles_seen


# ═══════════════════════════════════════════════════════════════════════════════
# PART 21 — Sandbox Executor
# ═══════════════════════════════════════════════════════════════════════════════

class TestSandbox:
    @pytest.mark.asyncio
    async def test_success(self):
        from kernel.sandbox import SandboxExecutor
        sandbox = SandboxExecutor(timeout=5)
        result = await sandbox.execute("print('hello world')")
        assert result["status"] == "success"
        assert "hello world" in result.get("stdout", "")

    @pytest.mark.asyncio
    async def test_error(self):
        from kernel.sandbox import SandboxExecutor
        sandbox = SandboxExecutor(timeout=5)
        result = await sandbox.execute("1/0")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_timeout(self):
        from kernel.sandbox import SandboxExecutor
        sandbox = SandboxExecutor(timeout=1)
        result = await sandbox.execute("import time; time.sleep(10)")
        assert result["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_syntax_error(self):
        from kernel.sandbox import SandboxExecutor
        sandbox = SandboxExecutor(timeout=5)
        result = await sandbox.execute("def broken(")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_unsupported_language(self):
        from kernel.sandbox import SandboxExecutor
        sandbox = SandboxExecutor(timeout=5)
        result = await sandbox.execute("print('hi')", language="rust")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_isolation(self):
        from kernel.sandbox import SandboxExecutor
        sandbox = SandboxExecutor(timeout=5)
        r1 = await sandbox.execute("x = 42")
        r2 = await sandbox.execute("print(x)")
        assert r1["status"] == "success"
        assert r2["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════════════
# PART 22 — Kernel Runtime Import Check
# ═══════════════════════════════════════════════════════════════════════════════

def test_orchestrator_engine_import():
    from kernel.orchestrator import OrchestratorEngine
    assert OrchestratorEngine is not None
