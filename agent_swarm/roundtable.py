"""
Roundtable — ระบบประชุมร่วมของ Agent ทุกตัว
เมื่อมีปัญหาใหญ่ ทุก Agent ระดมความคิด แล้ว Orchestrator ตัดสินใจ
"""

import time
import logging
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .message_bus import EventBus, get_event_bus
from .agents.base_agent import BaseAgent

logger = logging.getLogger("NEXUS-Roundtable")


@dataclass
class RoundtableSession:
    id: str = ""
    problem: str = ""
    opinions: Dict[str, str] = field(default_factory=dict)
    consensus: str = ""
    status: str = "collecting"  # collecting, deciding, done
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class Roundtable:
    """Agent Roundtable — all agents discuss a problem, then synthesize."""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.sessions: List[RoundtableSession] = []
        self._lock = threading.RLock()

    def convene(self, problem: str, agents: Dict[str, BaseAgent],
                timeout: float = 30.0) -> RoundtableSession:
        """Convene a roundtable discussion."""
        session = RoundtableSession(
            id=f"rt_{int(time.time())}",
            problem=problem,
        )
        self.sessions.append(session)

        logger.info(f"🏛️ Roundtable convened: {problem[:60]} | {len(agents)} agents")

        # Collect opinions in parallel
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
            futures = {}
            for name, agent in agents.items():
                future = executor.submit(agent.analyze_problem, problem)
                futures[future] = name

            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                name = futures[future]
                try:
                    opinion = future.result()
                    session.opinions[name] = opinion
                    self.event_bus.emit("roundtable:opinion", {
                        "session": session.id, "agent": name, "opinion": opinion,
                    })
                except Exception as e:
                    session.opinions[name] = f"ERROR: {e}"

        # Synthesize
        session.consensus = self._synthesize(session)
        session.status = "done"
        session.completed_at = time.time()

        logger.info(f"🏛️ Roundtable done: {len(session.opinions)} opinions collected")
        return session

    def _synthesize(self, session: RoundtableSession) -> str:
        """Combine all opinions into consensus."""
        lines = [f"📋 Roundtable Consensus: {session.problem[:60]}\n"]
        lines.append(f"👥 Agents consulted: {len(session.opinions)}\n")

        for agent, opinion in session.opinions.items():
            lines.append(f"▸ {agent.upper()}:")
            lines.append(f"  {opinion}\n")

        # Priority scoring
        lines.append("🎯 RECOMMENDED ACTIONS:")
        lines.append("1. Start with research (Researcher)")
        lines.append("2. Design architecture (Coder)")
        lines.append("3. Document plan (Writer)")
        lines.append("4. Track metrics (Analyst)")

        duration = (session.completed_at or time.time()) - session.started_at
        lines.append(f"\n⏱️ Roundtable completed in {duration:.1f}s")

        return "\n".join(lines)

    def get_latest(self) -> Optional[RoundtableSession]:
        return self.sessions[-1] if self.sessions else None

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total_sessions": len(self.sessions),
                "total_opinions": sum(len(s.opinions) for s in self.sessions),
            }


# Global instance
_roundtable: Optional[Roundtable] = None


def get_roundtable() -> Roundtable:
    global _roundtable
    if _roundtable is None:
        _roundtable = Roundtable()
    return _roundtable
