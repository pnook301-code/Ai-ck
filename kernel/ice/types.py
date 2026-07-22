"""ICE types"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import time
import uuid


@dataclass
class IterationResult:
    iteration: int
    role: str
    action: str
    content: str
    sandbox_result: Optional[Dict] = None
    scores: Dict[str, float] = field(default_factory=dict)
    decision: str = "continue"
    feedback: str = ""
    id: str = field(default_factory=lambda: f"ice_{uuid.uuid4().hex[:12]}")
    timestamp: float = field(default_factory=time.time)


class ROLES:
    ARCHITECT = "Architect"
    CRITIC = "Critic"
    JUDGE = "Judge"
    ORDER = [ARCHITECT, CRITIC, JUDGE]
