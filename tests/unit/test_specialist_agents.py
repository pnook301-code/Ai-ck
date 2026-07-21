"""Tests for Specialist Agents"""

import pytest
from kernel.agents.specialists import (
    CoderAgent, TesterAgent, DevOpsAgent,
    ResearcherAgent, SecurityAgent, ReviewerAgent,
)
from kernel.agents.types import AgentTask, AgentCapability, AgentStatus


@pytest.mark.asyncio
class TestCoderAgent:
    @pytest.fixture
    def agent(self):
        return CoderAgent()

    async def test_initialization(self, agent):
        assert agent.name == "coder"
        assert agent.status == AgentStatus.IDLE
        caps = agent.capabilities
        assert AgentCapability.CODE_WRITE in caps

    async def test_capabilities(self, agent):
        caps = agent.capabilities
        assert AgentCapability.CODE_REVIEW in caps
        assert AgentCapability.CODE_REFACTOR in caps
        assert AgentCapability.CODE_DEBUG in caps

    async def test_process_implement(self, agent):
        task = AgentTask(title="impl", description="implement a python function")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None

    async def test_process_refactor(self, agent):
        task = AgentTask(title="ref", description="refactor the code for performance")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert "refactored" in result.result.get("status", "")

    async def test_process_debug(self, agent):
        task = AgentTask(title="fix", description="debug the null pointer bug")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert "debugged" in result.result.get("status", "")

    async def test_process_review(self, agent):
        task = AgentTask(title="rev", description="review the pull request")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert "review" in result.result.get("output", "")


@pytest.mark.asyncio
class TestTesterAgent:
    @pytest.fixture
    def agent(self):
        return TesterAgent()

    async def test_initialization(self, agent):
        assert agent.name == "tester"
        caps = agent.capabilities
        assert AgentCapability.TEST_CREATE in caps
        assert AgentCapability.TEST_EXECUTE in caps

    async def test_process_unit_test(self, agent):
        task = AgentTask(title="unit", description="write unit tests for calculator module")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result.get("status") == "tests_created"

    async def test_process_integration_test(self, agent):
        task = AgentTask(title="integration", description="create integration test for api service")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result.get("status") == "tests_created"


@pytest.mark.asyncio
class TestDevOpsAgent:
    @pytest.fixture
    def agent(self):
        return DevOpsAgent()

    async def test_initialization(self, agent):
        assert agent.name == "devops"
        caps = agent.capabilities
        assert AgentCapability.DEPLOY in caps
        assert AgentCapability.MONITOR in caps

    async def test_process_dockerfile(self, agent):
        task = AgentTask(title="docker", description="generate dockerfile for python service")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None

    async def test_process_deployment(self, agent):
        task = AgentTask(title="deploy", description="create deployment plan for production")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None


@pytest.mark.asyncio
class TestResearcherAgent:
    @pytest.fixture
    def agent(self):
        return ResearcherAgent()

    async def test_initialization(self, agent):
        assert agent.name == "researcher"
        assert AgentCapability.RESEARCH in agent.capabilities

    async def test_process_literature_review(self, agent):
        task = AgentTask(title="lit review", description="literature review on multi-agent systems")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None

    async def test_process_feasibility(self, agent):
        task = AgentTask(title="feasibility", description="feasibility study for knowledge graphs")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None


@pytest.mark.asyncio
class TestSecurityAgent:
    @pytest.fixture
    def agent(self):
        return SecurityAgent()

    async def test_initialization(self, agent):
        assert agent.name == "security"
        assert AgentCapability.SECURITY_AUDIT in agent.capabilities
        assert AgentCapability.VULN_SCAN in agent.capabilities

    async def test_process_audit(self, agent):
        task = AgentTask(title="audit", description="perform security audit on auth module")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None

    async def test_process_threat_model(self, agent):
        task = AgentTask(title="threat", description="threat modeling for microservices architecture")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None


@pytest.mark.asyncio
class TestReviewerAgent:
    @pytest.fixture
    def agent(self):
        return ReviewerAgent()

    async def test_initialization(self, agent):
        assert agent.name == "reviewer"
        assert AgentCapability.REVIEW in agent.capabilities

    async def test_process_review(self, agent):
        task = AgentTask(title="review", description="review the code for best practices")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert "review" in result.result.get("type", "")

    async def test_process_best_practices(self, agent):
        task = AgentTask(title="best practices", description="check best practices for python project")
        result = await agent.execute(task)
        assert result.status == "completed"
        assert result.result is not None
