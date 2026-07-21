import asyncio
import pytest
from kernel.agents import (
    AgentMessage, AgentTask, AgentStatus, AgentCapability,
    BaseAgent, AgentRegistry, OrchestratorAgent, AgentManager,
)
from kernel.events import EventBus


class TestAgentMessage:
    def test_create_message(self):
        msg = AgentMessage(sender="a", receiver="b", msg_type="task", content={"key": "val"})
        assert msg.sender == "a"
        assert msg.receiver == "b"
        assert msg.msg_type == "task"
        assert msg.content["key"] == "val"
        assert msg.id.startswith("msg_")

    def test_to_dict(self):
        msg = AgentMessage(sender="a", receiver="b", msg_type="hello", content={"x": 1})
        d = msg.to_dict()
        assert d["sender"] == "a"
        assert d["type"] == "hello"
        assert d["content"]["x"] == 1

    def test_from_dict(self):
        data = {"sender": "a", "receiver": "b", "type": "reply", "content": {"ok": True}}
        msg = AgentMessage.from_dict(data)
        assert msg.sender == "a"
        assert msg.msg_type == "reply"
        assert msg.content["ok"] is True


class TestAgentTask:
    def test_create_task(self):
        t = AgentTask(title="Test Task", description="Do something")
        assert t.title == "Test Task"
        assert t.status == "pending"
        assert t.id.startswith("task_")

    def test_complete(self):
        t = AgentTask(title="t", description="d")
        t.complete({"success": True})
        assert t.status == "completed"
        assert t.result["success"] is True

    def test_fail(self):
        t = AgentTask(title="t", description="d")
        t.fail("something broke")
        assert t.status == "failed"
        assert "something broke" in t.result["error"]

    def test_to_dict(self):
        t = AgentTask(title="t", description="d", priority="high")
        d = t.to_dict()
        assert d["title"] == "t"
        assert d["priority"] == "high"
        assert d["status"] == "pending"


class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_create_agent(self):
        agent = BaseAgent(name="test", role="worker")
        assert agent.name == "test"
        assert agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_initialize(self):
        agent = BaseAgent(name="test", role="worker")
        await agent.initialize()
        assert agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_receive_message(self):
        agent = BaseAgent(name="a", role="worker")
        msg = AgentMessage(sender="b", receiver="a", msg_type="hello", content={})
        await agent.receive(msg)
        assert len(agent.inbox) == 1

    @pytest.mark.asyncio
    async def test_send_message(self):
        agent = BaseAgent(name="a", role="worker")
        msg = await agent.send("b", "task", {"action": "run"})
        assert msg.sender == "a"
        assert msg.receiver == "b"
        assert msg.msg_type == "task"
        assert len(agent.outbox) == 1

    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        class TestWorker(BaseAgent):
            async def _do_task(self, task):
                return {"processed": True}

        agent = TestWorker(name="worker", role="worker")
        task = AgentTask(title="test", description="do it")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result["processed"] is True
        assert agent.tasks_completed == 1

    @pytest.mark.asyncio
    async def test_execute_task_failure(self):
        class FailingWorker(BaseAgent):
            async def _do_task(self, task):
                raise RuntimeError("task error")

        agent = FailingWorker(name="failing", role="worker")
        task = AgentTask(title="fail", description="will fail")
        result = await agent.execute(task)
        assert result.status == "failed"
        assert "task error" in result.result["error"]
        assert agent.tasks_failed == 1

    @pytest.mark.asyncio
    async def test_get_status(self):
        class TestWorker(BaseAgent):
            async def _do_task(self, task):
                return {"ok": True}

        agent = TestWorker(name="worker", role="worker",
                           capabilities={AgentCapability.CODE_WRITE})
        s = agent.get_status()
        assert s["name"] == "worker"
        assert s["role"] == "worker"
        assert s["status"] == "idle"
        assert "write_code" in s["capabilities"]

    @pytest.mark.asyncio
    async def test_get_log(self):
        class TestWorker(BaseAgent):
            async def _do_task(self, task):
                return {}

        agent = TestWorker(name="w", role="w")
        task = AgentTask(title="t", description="d")
        await agent.execute(task)
        log = agent.get_log()
        assert len(log) >= 2

    @pytest.mark.asyncio
    async def test_stop(self):
        agent = BaseAgent(name="test", role="worker")
        await agent.stop()
        assert agent.status == AgentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_event_bus_integration(self):
        bus = EventBus()
        events = []

        async def handler(event):
            events.append(event.name)

        bus.on("agent.task.completed", handler)
        bus.on("agent.task.started", handler)

        class EventWorker(BaseAgent):
            async def _do_task(self, task):
                return {"ok": True}

        agent = EventWorker(name="ev", role="w", event_bus=bus)
        task = AgentTask(title="t", description="d")
        await agent.execute(task)
        await asyncio.sleep(0.05)
        assert "agent.task.started" in events
        assert "agent.task.completed" in events


class TestAgentRegistry:
    @pytest.mark.asyncio
    async def test_register_and_get(self):
        reg = AgentRegistry()
        agent = BaseAgent(name="a", role="worker")
        reg.register(agent)
        assert reg.get("a") is agent

    @pytest.mark.asyncio
    async def test_unregister(self):
        reg = AgentRegistry()
        agent = BaseAgent(name="a", role="worker")
        reg.register(agent)
        reg.unregister("a")
        assert reg.get("a") is None

    @pytest.mark.asyncio
    async def test_list_agents(self):
        reg = AgentRegistry()
        reg.register(BaseAgent(name="a", role="w"))
        reg.register(BaseAgent(name="b", role="w"))
        assert len(reg.list_agents()) == 2

    @pytest.mark.asyncio
    async def test_find_by_capability(self):
        reg = AgentRegistry()
        a1 = BaseAgent(name="coder", role="dev", capabilities={AgentCapability.CODE_WRITE})
        a2 = BaseAgent(name="tester", role="qa", capabilities={AgentCapability.TEST_EXECUTE})
        reg.register(a1)
        reg.register(a2)
        results = reg.find_by_capability(AgentCapability.CODE_WRITE)
        assert len(results) == 1
        assert results[0].name == "coder"

    @pytest.mark.asyncio
    async def test_find_by_role(self):
        reg = AgentRegistry()
        reg.register(BaseAgent(name="a", role="worker"))
        reg.register(BaseAgent(name="b", role="worker"))
        reg.register(BaseAgent(name="c", role="manager"))
        assert len(reg.find_by_role("worker")) == 2

    @pytest.mark.asyncio
    async def test_get_names(self):
        reg = AgentRegistry()
        reg.register(BaseAgent(name="a", role="w"))
        reg.register(BaseAgent(name="b", role="w"))
        assert sorted(reg.get_names()) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_count(self):
        reg = AgentRegistry()
        assert reg.count() == 0
        reg.register(BaseAgent(name="a", role="w"))
        assert reg.count() == 1


class TestOrchestratorAgent:
    @pytest.mark.asyncio
    async def test_plan_creates_steps(self):
        reg = AgentRegistry()
        orch = OrchestratorAgent(agent_registry=reg)
        plan = await orch.plan("write a new feature")
        assert len(plan["steps"]) > 0
        assert plan["status"] == "ready"

    @pytest.mark.asyncio
    async def test_plan_identifies_code_tasks(self):
        orch = OrchestratorAgent()
        plan = await orch.plan("implement login page")
        agents = [s["agent"] for s in plan["steps"]]
        assert "coder" in agents
        assert "tester" in agents

    @pytest.mark.asyncio
    async def test_plan_identifies_security_tasks(self):
        orch = OrchestratorAgent()
        plan = await orch.plan("run security audit")
        agents = [s["agent"] for s in plan["steps"]]
        assert "security" in agents

    @pytest.mark.asyncio
    async def test_plan_identifies_deploy_tasks(self):
        orch = OrchestratorAgent()
        plan = await orch.plan("deploy to production")
        agents = [s["agent"] for s in plan["steps"]]
        assert "devops" in agents

    @pytest.mark.asyncio
    async def test_plan_falls_back_to_generic(self):
        orch = OrchestratorAgent()
        plan = await orch.plan("do something random")
        assert len(plan["steps"]) == 4

    @pytest.mark.asyncio
    async def test_execute_plan_skips_missing_agents(self):
        reg = AgentRegistry()
        orch = OrchestratorAgent(agent_registry=reg)
        plan = await orch.plan("implement feature")
        result = await orch.execute_plan(plan)
        skipped = [s for s in result["results"] if s["status"] == "skipped"]
        assert len(skipped) > 0

    @pytest.mark.asyncio
    async def test_execute_plan_with_registered_agents(self):
        reg = AgentRegistry()

        class TestCoder(BaseAgent):
            async def _do_task(self, task):
                return {"code": "written"}

        class TestTester(BaseAgent):
            async def _do_task(self, task):
                return {"tests": "passed"}

        reg.register(TestCoder(name="coder", role="dev",
                    capabilities={AgentCapability.CODE_WRITE}))
        reg.register(TestTester(name="tester", role="qa",
                    capabilities={AgentCapability.TEST_EXECUTE}))

        orch = OrchestratorAgent(agent_registry=reg)
        plan = await orch.plan("implement and test feature")
        result = await orch.execute_plan(plan)

        completed = [s for s in result["results"] if s["status"] == "completed"]
        assert len(completed) > 0

    @pytest.mark.asyncio
    async def test_delegate(self):
        reg = AgentRegistry()

        class TestAgent(BaseAgent):
            async def _do_task(self, task):
                return {"done": True}

        reg.register(TestAgent(name="worker", role="w"))
        orch = OrchestratorAgent(agent_registry=reg)
        result = await orch.delegate("worker", "do something")
        assert result.status == "completed"
        assert result.result["done"] is True

    @pytest.mark.asyncio
    async def test_delegate_missing_agent(self):
        reg = AgentRegistry()
        orch = OrchestratorAgent(agent_registry=reg)
        result = await orch.delegate("nonexistent", "task")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_event_bus_integration(self):
        bus = EventBus()
        events = []

        async def handler(event):
            events.append(event.name)

        bus.on("orchestrator.plan.created", handler)
        bus.on("orchestrator.plan.completed", handler)

        reg = AgentRegistry()

        class T(BaseAgent):
            async def _do_task(self, task):
                return {}

        reg.register(T(name="coder", role="d"))
        orch = OrchestratorAgent(agent_registry=reg, event_bus=bus)
        plan = await orch.plan("implement")
        await orch.execute_plan(plan)
        await asyncio.sleep(0.05)
        assert "orchestrator.plan.created" in events


class TestAgentManager:
    @pytest.mark.asyncio
    async def test_register_agent(self):
        mgr = AgentManager()
        agent = BaseAgent(name="a", role="w")
        mgr.register_agent(agent)
        assert mgr.get_agent("a") is agent

    @pytest.mark.asyncio
    async def test_get_all_agents(self):
        mgr = AgentManager()
        mgr.register_agent(BaseAgent(name="a", role="w"))
        mgr.register_agent(BaseAgent(name="b", role="w"))
        assert len(mgr.get_all_agents()) == 2

    @pytest.mark.asyncio
    async def test_execute_completes(self):
        mgr = AgentManager()

        class Coder(BaseAgent):
            async def _do_task(self, task):
                return {"code": "done"}

        class Tester(BaseAgent):
            async def _do_task(self, task):
                return {"tests": "pass"}

        mgr.register_agent(Coder(name="coder", role="dev"))
        mgr.register_agent(Tester(name="tester", role="qa"))
        report = await mgr.execute("implement feature")
        assert report["summary"]["total_steps"] > 0
        assert "success_rate" in report["summary"]

    @pytest.mark.asyncio
    async def test_delegate(self):
        mgr = AgentManager()

        class TestAgent(BaseAgent):
            async def _do_task(self, task):
                return {"done": True}

        mgr.register_agent(TestAgent(name="w", role="w"))
        result = await mgr.delegate("w", "do it")
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_delegate_missing(self):
        mgr = AgentManager()
        result = await mgr.delegate("nonexistent", "task")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_status(self):
        mgr = AgentManager()
        mgr.register_agent(BaseAgent(name="a", role="w"))
        s = mgr.get_status()
        assert s["agents"] == 1
        assert "a" in s["agent_names"]
