"""
SharedMemory — SQLite-backed shared context for Agent Swarm
ทุก Agent อ่าน/เขียนข้อมูลร่วมกัน
"""

import os
import json
import time
import sqlite3
import threading
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("NEXUS-SharedMemory")

DB_PATH = "/workspace/ck-nexus/agent_swarm_memory.db"


@dataclass
class MemoryEntry:
    key: str
    value: Any
    agent_name: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ttl: float = 0  # 0 = no expiry
    tags: List[str] = field(default_factory=list)


class SharedMemory:
    """SQLite-backed shared memory pool for Agent Swarm."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS swarm_memory (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    agent_name TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    ttl REAL DEFAULT 0,
                    tags TEXT DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_swarm_memory_tags
                ON swarm_memory(tags)
            """)
            conn.commit()
            conn.close()
            logger.info(f"SharedMemory initialized: {self.db_path}")

    def save(self, key: str, value: Any, agent_name: str = "",
             ttl: float = 0, tags: List[str] = None):
        """Save or update memory entry."""
        now = time.time()
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO swarm_memory (key, value, agent_name, created_at, updated_at, ttl, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    agent_name=excluded.agent_name,
                    updated_at=excluded.updated_at,
                    ttl=excluded.ttl,
                    tags=excluded.tags
            """, (key, json.dumps(value, ensure_ascii=False), agent_name,
                  now, now, ttl, json.dumps(tags or [])))
            conn.commit()
            conn.close()

    def get(self, key: str) -> Optional[Any]:
        """Get memory entry by key."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT value, ttl, created_at FROM swarm_memory WHERE key=?", (key,)
            ).fetchone()
            conn.close()

            if row is None:
                return None

            value, ttl, created_at = row
            if ttl > 0 and (time.time() - created_at) > ttl:
                self.delete(key)
                return None

            return json.loads(value)

    def delete(self, key: str):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM swarm_memory WHERE key=?", (key,))
            conn.commit()
            conn.close()

    def search(self, tag: str = None, agent_name: str = None,
               limit: int = 100) -> List[Dict]:
        """Search memory entries."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT key, value, agent_name, created_at, tags FROM swarm_memory"
            params = []
            conditions = []

            if agent_name:
                conditions.append("agent_name=?")
                params.append(agent_name)
            if tag:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            conn.close()

            return [
                {"key": r[0], "value": json.loads(r[1]),
                 "agent": r[2], "created": r[3], "tags": json.loads(r[4])}
                for r in rows
            ]

    def get_all_keys(self) -> List[str]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT key FROM swarm_memory").fetchall()
            conn.close()
            return [r[0] for r in rows]

    def clear(self, agent_name: str = None):
        """Clear all entries, optionally only for a specific agent."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            if agent_name:
                conn.execute("DELETE FROM swarm_memory WHERE agent_name=?", (agent_name,))
            else:
                conn.execute("DELETE FROM swarm_memory")
            conn.commit()
            conn.close()

    def get_stats(self) -> Dict:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            total = conn.execute("SELECT COUNT(*) FROM swarm_memory").fetchone()[0]
            agents = conn.execute(
                "SELECT agent_name, COUNT(*) FROM swarm_memory GROUP BY agent_name"
            ).fetchall()
            conn.close()
            return {
                "total_entries": total,
                "by_agent": {a: c for a, c in agents},
            }


# Global instance
_shared_memory: Optional[SharedMemory] = None


def get_shared_memory() -> SharedMemory:
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedMemory()
    return _shared_memory
