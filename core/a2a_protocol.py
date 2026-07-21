#!/usr/bin/env python3
"""
A2A Protocol Implementation for CK-NEXUS
Agent-to-Agent communication for multi-agent systems
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class TaskState(Enum):
    """A2A Task States."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class AgentCard:
    """Agent discovery card (A2A standard)."""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: Dict = field(default_factory=lambda: {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False
    })
    skills: List[Dict] = field(default_factory=list)
    authentication: Dict = field(default_factory=lambda: {
        "schemes": ["none"]
    })
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "authentication": self.authentication
        }


@dataclass
class A2ATask:
    """A2A Task."""
    id: str
    session_id: str
    state: TaskState
    message: Dict
    artifacts: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "state": self.state.value,
            "message": self.message,
            "artifacts": self.artifacts,
            "history": self.history,
            "metadata": self.metadata
        }


class A2AAgent:
    """
    A2A-compliant agent that can communicate with other agents.
    """
    
    def __init__(self, name: str, description: str, url: str = "http://localhost:8080"):
        self.card = AgentCard(
            name=name,
            description=description,
            url=url
        )
        self.tasks: Dict[str, A2ATask] = {}
        self.skill_handlers: Dict[str, Callable] = {}
        self.peers: Dict[str, AgentCard] = {}
    
    def add_skill(self, name: str, description: str, handler: Callable):
        """Add a skill that this agent can perform."""
        self.card.skills.append({
            "id": name,
            "name": name,
            "description": description,
            "tags": []
        })
        self.skill_handlers[name] = handler
    
    def register_peer(self, card: AgentCard):
        """Register a peer agent."""
        self.peers[card.name] = card
    
    def create_task(self, message: str, session_id: str = None) -> A2ATask:
        """Create a new task."""
        task_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        
        task = A2ATask(
            id=task_id,
            session_id=session_id,
            state=TaskState.SUBMITTED,
            message={
                "role": "user",
                "parts": [{"type": "text", "text": message}]
            }
        )
        
        self.tasks[task_id] = task
        return task
    
    def process_task(self, task: A2ATask) -> A2ATask:
        """Process a task (override in subclasses)."""
        task.state = TaskState.WORKING
        task.updated_at = time.time()
        
        # Extract message text
        message_text = ""
        if "parts" in task.message:
            for part in task.message["parts"]:
                if part.get("type") == "text":
                    message_text = part["text"]
                    break
        
        # Try to find matching skill
        result = None
        for skill_name, handler in self.skill_handlers.items():
            if skill_name in message_text.lower():
                result = handler(message_text)
                break
        
        # Default response if no skill matched
        if result is None:
            result = f"Agent {self.card.name} received: {message_text[:100]}"
        
        # Create artifact
        task.artifacts.append({
            "name": "response",
            "parts": [{"type": "text", "text": result}]
        })
        
        task.state = TaskState.COMPLETED
        task.updated_at = time.time()
        task.history.append({
            "state": TaskState.SUBMITTED.value,
            "timestamp": task.created_at
        })
        task.history.append({
            "state": TaskState.COMPLETED.value,
            "timestamp": task.updated_at
        })
        
        return task
    
    def send_task(self, target_agent: str, message: str) -> Optional[A2ATask]:
        """Send a task to another agent."""
        if target_agent not in self.peers:
            print(f"Agent {target_agent} not found")
            return None
        
        # Create and process task locally (simulated)
        task = self.create_task(message)
        task = self.process_task(task)
        
        return task
    
    def get_agent_card(self) -> Dict:
        """Get agent card for discovery."""
        return self.card.to_dict()
    
    def get_tasks(self) -> List[Dict]:
        """Get all tasks."""
        return [task.to_dict() for task in self.tasks.values()]


class A2AOrchestrator:
    """
    Orchestrator for managing multiple A2A agents.
    Implements centralized orchestration pattern.
    """
    
    def __init__(self):
        self.agents: Dict[str, A2AAgent] = {}
        self.tasks: Dict[str, A2ATask] = {}
    
    def register_agent(self, agent: A2AAgent):
        """Register an agent with the orchestrator."""
        self.agents[agent.card.name] = agent
    
    def discover_agents(self) -> List[Dict]:
        """Discover all registered agents."""
        return [agent.get_agent_card() for agent in self.agents.values()]
    
    def route_task(self, message: str, preferred_agent: str = None) -> A2ATask:
        """Route a task to the best agent."""
        # Simple routing: use preferred agent or first available
        if preferred_agent and preferred_agent in self.agents:
            agent = self.agents[preferred_agent]
        else:
            # Find agent with matching skill
            agent = None
            for a in self.agents.values():
                for skill in a.card.skills:
                    if skill["name"].lower() in message.lower():
                        agent = a
                        break
                if agent:
                    break
            
            # Fallback to first agent
            if not agent and self.agents:
                agent = list(self.agents.values())[0]
        
        if not agent:
            task = A2ATask(
                id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                state=TaskState.FAILED,
                message={"role": "user", "parts": [{"type": "text", "text": message}]}
            )
            return task
        
        # Create and process task
        task = agent.create_task(message)
        task = agent.process_task(task)
        self.tasks[task.id] = task
        
        return task
    
    def get_system_status(self) -> Dict:
        """Get system status."""
        return {
            "agents": list(self.agents.keys()),
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.state == TaskState.COMPLETED),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.state == TaskState.FAILED)
        }


# Pre-configured CK-NEXUS agents
def create_ck_nexus_agents() -> A2AOrchestrator:
    """Create pre-configured agents for CK-NEXUS."""
    orchestrator = A2AOrchestrator()
    
    # Research Agent
    research = A2AAgent(
        name="researcher",
        description="Researches information from web and knowledge base",
        url="http://localhost:8081"
    )
    research.add_skill("research", "Research a topic", 
                      lambda msg: f"Researching: {msg[:50]}...")
    orchestrator.register_agent(research)
    
    # Coder Agent
    coder = A2AAgent(
        name="coder",
        description="Writes and reviews code",
        url="http://localhost:8082"
    )
    coder.add_skill("code", "Write code",
                   lambda msg: f"```python\n# Code for: {msg[:30]}\nprint('Hello')\n```")
    orchestrator.register_agent(coder)
    
    # Memory Agent
    memory = A2AAgent(
        name="memory",
        description="Manages and retrieves memories",
        url="http://localhost:8083"
    )
    memory.add_skill("remember", "Store information",
                    lambda msg: f"Remembered: {msg[:50]}")
    memory.add_skill("recall", "Retrieve information",
                    lambda msg: f"Recalled: {msg[:50]}")
    orchestrator.register_agent(memory)
    
    # Review Agent
    reviewer = A2AAgent(
        name="reviewer",
        description="Reviews and validates output",
        url="http://localhost:8084"
    )
    reviewer.add_skill("review", "Review content",
                     lambda msg: f"Review: {msg[:50]} - Looks good!")
    orchestrator.register_agent(reviewer)
    
    return orchestrator


if __name__ == "__main__":
    orchestrator = create_ck_nexus_agents()
    
    print("🤖 A2A Multi-Agent System")
    print("=" * 60)
    
    # Discover agents
    agents = orchestrator.discover_agents()
    print(f"\n📡 Registered Agents ({len(agents)}):")
    for agent in agents:
        skills = [s["name"] for s in agent["skills"]]
        print(f"   🤖 {agent['name']}: {agent['description']}")
        print(f"      Skills: {skills}")
    
    # Route tasks
    print("\n📨 Routing Tasks:")
    
    result = orchestrator.route_task("research AI trends")
    print(f"\n   Task: 'research AI trends'")
    print(f"   Agent: researcher")
    print(f"   Result: {result.artifacts[0]['parts'][0]['text'][:60]}...")
    
    result = orchestrator.route_task("write code for API")
    print(f"\n   Task: 'write code for API'")
    print(f"   Agent: coder")
    print(f"   Result: {result.artifacts[0]['parts'][0]['text'][:60]}...")
    
    result = orchestrator.route_task("remember user preferences")
    print(f"\n   Task: 'remember user preferences'")
    print(f"   Agent: memory")
    print(f"   Result: {result.artifacts[0]['parts'][0]['text'][:60]}...")
    
    # Status
    print(f"\n📊 Status: {orchestrator.get_system_status()}")
    
    print("\n" + "=" * 60)
    print("✅ A2A System Ready!")
