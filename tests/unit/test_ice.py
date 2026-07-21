"""Tests for Iterative Consensus Engine"""

import pytest
from kernel.ice import (
    IterativeConsensusEngine, IterationResult, ROLES,
    ArchitectAgent, CriticAgent, JudgeAgent,
)
from kernel.agents.types import AgentTask, AgentStatus


class TestICEAgents:
    def test_architect_initialization(self):
        agent = ArchitectAgent()
        assert agent.name == "architect"
        assert agent.status == AgentStatus.IDLE

    def test_critic_initialization(self):
        agent = CriticAgent()
        assert agent.name == "critic"

    def test_judge_initialization(self):
        agent = JudgeAgent(threshold=90.0)
        assert agent.name == "judge"
        assert agent._threshold == 90.0

    @pytest.mark.asyncio
    async def test_architect_execute(self):
        agent = ArchitectAgent()
        task = AgentTask(title="design", description="Build an API")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert "designed" in result.result.get("status", "")

    @pytest.mark.asyncio
    async def test_critic_execute(self):
        agent = CriticAgent()
        task = AgentTask(title="review", description="Review the code")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result.get("scores", {}).get("overall", 0) > 0

    @pytest.mark.asyncio
    async def test_judge_execute_pass(self):
        agent = JudgeAgent(threshold=50)
        task = AgentTask(title="judge", description="Judge the work",
                         metadata={"scores": {"overall": 80}})
        result = await agent.execute(task)
        assert result.result.get("decision") == "TERMINATE_LOOP"

    @pytest.mark.asyncio
    async def test_judge_execute_fail(self):
        agent = JudgeAgent(threshold=95, event_bus=None)
        task = AgentTask(title="judge", description="Judge the work",
                         metadata={"scores": {"overall": 50}})
        result = await agent.execute(task)
        assert result.result.get("decision") == "continue"


class TestICE:
    def test_roles_order(self):
        assert ROLES.ORDER == ["Architect", "Critic", "Judge"]

    def test_iteration_result_defaults(self):
        r = IterationResult(iteration=1, role="Architect", action="create", content="test")
        assert r.id.startswith("ice_")
        assert r.decision == "continue"

    @pytest.mark.asyncio
    async def test_ice_run_terminates(self):
        ice = IterativeConsensusEngine(max_iterations=3, judge_threshold=50)
        report = await ice.run(task="test task")
        assert report["success"] is True
        assert 1 <= report["total_iterations"] <= 3

    @pytest.mark.asyncio
    async def test_ice_max_iterations(self):
        ice = IterativeConsensusEngine(max_iterations=5, judge_threshold=99)
        report = await ice.run(task="hard task")
        assert report["total_iterations"] <= 5

    def test_ice_history_summary(self):
        ice = IterativeConsensusEngine()
        assert "No previous" in ice._summarize_history()
        ice.history.append(IterationResult(1, "Architect", "code", "built", feedback="implemented"))
        summary = ice._summarize_history()
        assert "implemented" in summary


class TestSandbox:
    @pytest.mark.asyncio
    async def test_sandbox_success(self):
        from kernel.sandbox import SandboxExecutor
        ex = SandboxExecutor(timeout=5)
        result = await ex.execute("print('hello')")
        assert result["status"] == "success"
        assert "hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_sandbox_error(self):
        from kernel.sandbox import SandboxExecutor
        ex = SandboxExecutor(timeout=5)
        result = await ex.execute("1/0")
        assert result["status"] == "error"
        assert result["stderr"] != ""

    @pytest.mark.asyncio
    async def test_sandbox_timeout(self):
        from kernel.sandbox import SandboxExecutor
        ex = SandboxExecutor(timeout=1)
        result = await ex.execute("import time; time.sleep(10)")
        assert result["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_sandbox_unsupported_language(self):
        from kernel.sandbox import SandboxExecutor
        ex = SandboxExecutor()
        result = await ex.execute("print('test')", language="ruby")
        assert result["status"] == "error"
